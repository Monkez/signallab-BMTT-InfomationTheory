import { forwardRef, type CSSProperties } from 'react'
import { curveDomain, styleDash } from './chartMath'
import { previewChart, reportChart } from './constants'
import type { BerCurve } from './types'
import { BerLegend } from './BerLegend'

type BerPlotProps = {
  curves: BerCurve[]
  variant?: 'preview' | 'report'
}

export const BerPlot = forwardRef<SVGSVGElement, BerPlotProps>(function BerPlot({ curves, variant = 'preview' }, ref) {
  const geometry = variant === 'report' ? reportChart : previewChart
  const isReport = variant === 'report'
  const { minX, maxX, xRange, maxLog, minLog, yRange } = curveDomain(curves)
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
  const tickCount = isReport ? 5 : 4
  const yTicks = Array.from({ length: tickCount }, (_, index) => maxLog - (index * yRange) / (tickCount - 1))
  const xTicks = isReport ? Array.from({ length: 5 }, (_, index) => minX + (index * xRange) / 4) : [minX, maxX]
  const labelStyle: CSSProperties = { fontSize: isReport ? 14 : 9, fill: '#68778b' }

  return <svg
    ref={ref}
    className={isReport ? 'ber-report-plot' : undefined}
    viewBox={`0 0 ${geometry.width} ${geometry.height}`}
    role="img"
    aria-label={isReport ? 'Detailed bit error rate versus SNR chart' : 'Bit error rate versus SNR chart'}
    shapeRendering="geometricPrecision"
    textRendering="geometricPrecision"
  >
    <rect x={geometry.left} y={geometry.top} width={plotWidth} height={plotHeight} fill="#f8fafc" stroke="#cfd8e4" strokeWidth={isReport ? 1.5 : 1} />
    {yTicks.map((tick, index) => {
      const yy = geometry.top + (index / (tickCount - 1)) * plotHeight
      return <g key={`y-${index}`}><line x1={geometry.left} x2={geometry.width - geometry.right} y1={yy} y2={yy} stroke="#e1e7ef" strokeWidth={isReport ? 1.25 : 1} /><text x={geometry.left - (isReport ? 14 : 7)} y={yy + (isReport ? 5 : 3)} textAnchor="end" style={labelStyle}>{`1e${tick.toFixed(isReport ? 1 : 0).replace('.0', '')}`}</text></g>
    })}
    {xTicks.map((tick, index) => {
      const xx = x(tick)
      return <g key={`x-${index}`}>{isReport && <line x1={xx} x2={xx} y1={geometry.top} y2={geometry.height - geometry.bottom} stroke="#edf1f5" strokeWidth="1" />}<text x={xx} y={isReport ? geometry.height - geometry.bottom + 25 : geometry.height - 17} textAnchor="middle" style={labelStyle}>{tick.toFixed(1)}</text></g>
    })}
    {curves.map((curve, curveIndex) => <g key={curve.id}>
      {lineFor(curve) && <polyline points={lineFor(curve)} fill="none" stroke={curve.color} strokeWidth={isReport ? (curveIndex === 0 ? 3.2 : 2.6) : (curveIndex === 0 ? 2.5 : 2)} strokeDasharray={styleDash(curve.style)} strokeLinecap="round" strokeLinejoin="round" opacity={curveIndex === 0 ? 1 : 0.86} />}
      {curve.plotted.filter(point => point.ber !== 0).map(point => <circle key={`${curve.id}-${point.snr_db}-${point.frames}`} cx={x(point.snr_db)} cy={y(Number(point.ber ?? 0))} r={isReport ? (curveIndex === 0 ? 5.5 : 4.6) : (curveIndex === 0 ? 3.5 : 3)} fill={curve.color} stroke="#fff" strokeWidth={isReport ? 2 : 1.5}><title>{`${curve.name} · ${point.snr_db} dB: BER ${point.ber ?? 0}`}</title></circle>)}
    </g>)}
    <BerLegend
      curves={curves}
      report={isReport}
      width={isReport ? 230 : 126}
      x={geometry.width - geometry.right - (isReport ? 230 : 126) - (isReport ? 12 : 6)}
      y={geometry.top + (isReport ? 12 : 6)}
    />
    <text x={geometry.width / 2} y={geometry.height - (isReport ? 8 : 5)} textAnchor="middle" style={{ ...labelStyle, fontSize: isReport ? 16 : 9 }}>SNR (dB)</text>
    <text x={isReport ? 22 : 11} y={geometry.height / 2} textAnchor="middle" transform={`rotate(-90 ${isReport ? 22 : 11} ${geometry.height / 2})`} style={{ ...labelStyle, fontSize: isReport ? 16 : 9 }}>BER (log)</text>
  </svg>
})
