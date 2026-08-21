import { styleDash } from './chartMath'
import type { BerCurve } from './types'

type BerLegendProps = {
  curves: BerCurve[]
  x: number
  y: number
  width: number
  report?: boolean
}

/** SVG-native legend, kept inside the plotting area for technical BER charts. */
export function BerLegend({ curves, x, y, width, report = false }: BerLegendProps) {
  const rowHeight = report ? 23 : 15
  const padding = report ? 10 : 6
  const fontSize = report ? 11.5 : 8.5
  const lineWidth = report ? 30 : 20
  const visibleCurves = curves.slice(0, report ? 8 : 6)
  const height = padding * 2 + visibleCurves.length * rowHeight

  return <g className="ber-plot-legend" aria-label="BER curve legend" pointerEvents="none">
    <rect x={x} y={y} width={width} height={height} rx={report ? 7 : 4} fill="#ffffff" fillOpacity="0.94" stroke="#cfd8e4" />
    {visibleCurves.map((curve, index) => {
      const yy = y + padding + rowHeight * index + rowHeight / 2
      const maxNameLength = report ? 28 : 17
      const name = curve.name.length > maxNameLength ? `${curve.name.slice(0, maxNameLength - 1)}…` : curve.name
      return <g key={curve.id}>
        <line x1={x + padding} x2={x + padding + lineWidth} y1={yy} y2={yy} stroke={curve.color} strokeWidth={report ? 3 : 2.2} strokeDasharray={styleDash(curve.style)} strokeLinecap="round" />
        <text x={x + padding + lineWidth + (report ? 9 : 5)} y={yy + fontSize * 0.34} fill="#3f4e63" fontSize={fontSize} fontWeight="600">{name}</text>
      </g>
    })}
  </g>
}
