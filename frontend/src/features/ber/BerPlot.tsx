import { forwardRef, type CSSProperties } from 'react'
import { curveDomain, styleDash } from './chartMath'
import { previewChart, reportChart } from './constants'
import type { BerCurve } from './types'
import { BerLegend } from './BerLegend'

type BerPlotProps = {
  curves: BerCurve[]
  variant?: 'preview' | 'dashboard' | 'report'
}

export const BerPlot = forwardRef<SVGSVGElement, BerPlotProps>(function BerPlot({ curves, variant = 'preview' }, ref) {
  const expanded = variant !== 'preview'
  const geometry = expanded ? reportChart : previewChart
  const { minX, xRange, xTicks, maxLog, minLog, yRange } = curveDomain(curves, expanded ? 8 : 6)
  const plotWidth = geometry.width - geometry.left - geometry.right
  const plotHeight = geometry.height - geometry.top - geometry.bottom
  const x = (value: number) => geometry.left + ((value - minX) / xRange) * plotWidth
  const y = (value: number) => geometry.top + ((maxLog - Math.log10(Math.max(value, 1e-8))) / yRange) * plotHeight
  const lineFor = (curve: BerCurve) => {
    const nonZero = curve.firstZero >= 0 ? curve.plotted.slice(0, curve.firstZero) : curve.plotted
    const line = nonZero.map(point => `${x(point.snr_db)},${y(Number(point.ber ?? 0))}`)
    // BER = 0 is an upper-bound measurement. End the curve with a vertical drop
    // at the last non-zero sample; do not draw the zero marker or later samples.
    if (curve.firstZero > 0 && nonZero.length) line.push(`${x(nonZero[nonZero.length - 1].snr_db)},${y(0)}`)
    return line.join(' ')
  }
  const yMajorTicks = Array.from({ length: maxLog - minLog + 1 }, (_, index) => maxLog - index)
  const yMinorTicks = Array.from({ length: maxLog - minLog }, (_, decadeIndex) => {
    const exponent = minLog + decadeIndex
    return Array.from({ length: 8 }, (_, mantissaIndex) => exponent + Math.log10(mantissaIndex + 2))
  }).flat().filter(logValue => logValue > minLog && logValue < maxLog)
  const yFromLog = (logValue: number) => geometry.top + ((maxLog - logValue) / yRange) * plotHeight
  const xDecimals = xTicks.step >= 1 ? 0 : Math.min(3, Math.max(1, Math.ceil(-Math.log10(xTicks.step))))
  const labelStyle: CSSProperties = { fontSize: expanded ? 12 : 8.5, fill: '#68778b' }

  return <svg
    ref={ref}
    className={variant === 'report' ? 'ber-report-plot' : variant === 'dashboard' ? 'ber-dashboard-plot' : undefined}
    viewBox={`0 0 ${geometry.width} ${geometry.height}`}
    role="img"
    aria-label={variant === 'report' ? 'Detailed bit error rate versus SNR chart' : 'Bit error rate versus SNR chart'}
    shapeRendering="geometricPrecision"
    textRendering="geometricPrecision"
  >
    <rect x={geometry.left} y={geometry.top} width={plotWidth} height={plotHeight} fill="#f8fafc" stroke="#cfd8e4" strokeWidth={expanded ? 1.5 : 1} />
    {yMinorTicks.map((logValue, index) => {
      const yy = yFromLog(logValue)
      const mantissa = index % 8 + 2
      return <g key={`y-minor-${logValue}`}><line x1={geometry.left - (expanded ? 5 : 3)} x2={geometry.left} y1={yy} y2={yy} stroke="#aebccd" strokeWidth={expanded ? 1 : .75} />{(mantissa === 2 || mantissa === 5) && <line x1={geometry.left} x2={geometry.width - geometry.right} y1={yy} y2={yy} stroke="#edf1f5" strokeWidth={expanded ? .9 : .65} strokeDasharray={expanded ? '3 4' : '2 3'} />}</g>
    })}
    {xTicks.minor.map(tick => {
      const xx = x(tick)
      return <g key={`x-minor-${tick}`}><line x1={xx} x2={xx} y1={geometry.top} y2={geometry.height - geometry.bottom} stroke="#f0f3f7" strokeWidth={expanded ? .8 : .55} /><line x1={xx} x2={xx} y1={geometry.height - geometry.bottom} y2={geometry.height - geometry.bottom + (expanded ? 5 : 3)} stroke="#aebccd" strokeWidth={expanded ? 1 : .75} /></g>
    })}
    {yMajorTicks.map(tick => {
      const yy = yFromLog(tick)
      return <g key={`y-${tick}`}><line x1={geometry.left} x2={geometry.width - geometry.right} y1={yy} y2={yy} stroke="#dce4ed" strokeWidth={expanded ? 1.15 : .9} /><line x1={geometry.left - (expanded ? 9 : 5)} x2={geometry.left} y1={yy} y2={yy} stroke="#8393a7" strokeWidth={expanded ? 1.25 : 1} /><text x={geometry.left - (expanded ? 14 : 7)} y={yy + (expanded ? 4 : 3)} textAnchor="end" style={labelStyle}>{`1e${tick}`}</text></g>
    })}
    {xTicks.major.map(tick => {
      const xx = x(tick)
      return <g key={`x-${tick}`}><line x1={xx} x2={xx} y1={geometry.top} y2={geometry.height - geometry.bottom} stroke="#e2e8f0" strokeWidth={expanded ? 1 : .75} /><line x1={xx} x2={xx} y1={geometry.height - geometry.bottom} y2={geometry.height - geometry.bottom + (expanded ? 9 : 5)} stroke="#8393a7" strokeWidth={expanded ? 1.25 : 1} /><text x={xx} y={expanded ? geometry.height - geometry.bottom + 23 : geometry.height - 17} textAnchor="middle" style={labelStyle}>{tick.toFixed(xDecimals)}</text></g>
    })}
    {curves.map((curve, curveIndex) => <g key={curve.id}>
      {lineFor(curve) && <polyline points={lineFor(curve)} fill="none" stroke={curve.color} strokeWidth={expanded ? (curveIndex === 0 ? 3.2 : 2.6) : (curveIndex === 0 ? 2.5 : 2)} strokeDasharray={styleDash(curve.style)} strokeLinecap="round" strokeLinejoin="round" opacity={curveIndex === 0 ? 1 : 0.86} />}
      {curve.plotted.filter(point => point.ber !== 0).map(point => <circle key={`${curve.id}-${point.snr_db}-${point.frames}`} cx={x(point.snr_db)} cy={y(Number(point.ber ?? 0))} r={expanded ? (curveIndex === 0 ? 5.5 : 4.6) : (curveIndex === 0 ? 3.5 : 3)} fill={curve.color} stroke="#fff" strokeWidth={expanded ? 2 : 1.5}><title>{`${curve.name} · ${point.snr_db} dB: BER ${point.ber ?? 0}`}</title></circle>)}
    </g>)}
    <BerLegend
      curves={curves}
      report={expanded}
      width={expanded ? 230 : 126}
      x={geometry.width - geometry.right - (expanded ? 230 : 126) - (expanded ? 12 : 6)}
      y={geometry.top + (expanded ? 12 : 6)}
    />
    <text x={geometry.width / 2} y={geometry.height - (expanded ? 8 : 5)} textAnchor="middle" style={{ ...labelStyle, fontSize: expanded ? 14 : 9 }}>SNR (dB)</text>
    <text x={expanded ? 22 : 11} y={geometry.height / 2} textAnchor="middle" transform={`rotate(-90 ${expanded ? 22 : 11} ${geometry.height / 2})`} style={{ ...labelStyle, fontSize: expanded ? 14 : 9 }}>BER (log)</text>
  </svg>
})
