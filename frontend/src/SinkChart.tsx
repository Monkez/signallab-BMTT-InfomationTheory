import type { CSSProperties } from 'react'

export type SinkPoint = {
  snr_db: number
  bit_errors: number
  total_bits: number
  frames: number
  ber: number | null
}

const chart = { width: 340, height: 190, left: 42, right: 12, top: 14, bottom: 30 }

export function BerChart({ points }: { points: SinkPoint[] }) {
  const valid = points.filter(point => Number.isFinite(point.snr_db) && point.total_bits > 0)
  if (!valid.length) return <div className="sink-chart empty">Run an experiment to see BER vs SNR.</div>

  const minX = Math.min(...valid.map(point => point.snr_db))
  const maxX = Math.max(...valid.map(point => point.snr_db))
  const xRange = Math.max(maxX - minX, 1)
  const values = valid.map(point => Math.max(Number(point.ber ?? 0), 1e-8))
  const maxLog = Math.ceil(Math.max(...values.map(value => Math.log10(value)), -1))
  const minLog = Math.min(-8, Math.floor(Math.min(...values.map(value => Math.log10(value)))))
  const yRange = Math.max(maxLog - minLog, 1)
  const x = (value: number) => chart.left + ((value - minX) / xRange) * (chart.width - chart.left - chart.right)
  const y = (value: number) => chart.top + ((maxLog - Math.log10(Math.max(value, 1e-8))) / yRange) * (chart.height - chart.top - chart.bottom)
  const line = valid.map(point => `${x(point.snr_db)},${y(Number(point.ber ?? 0))}`).join(' ')
  const labelStyle: CSSProperties = { fontSize: 9, fill: '#6b7788' }
  const yTicks = [0, 1, 2, 3].map(index => maxLog - (index * yRange) / 3)

  return <div className="sink-chart">
    <div className="sink-chart-title">BER vs SNR</div>
    <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Bit error rate versus SNR chart">
      <rect x={chart.left} y={chart.top} width={chart.width - chart.left - chart.right} height={chart.height - chart.top - chart.bottom} fill="#f8fafc" stroke="#d7dee8" />
      {yTicks.map((tick, index) => {
        const yy = chart.top + (index / 3) * (chart.height - chart.top - chart.bottom)
        return <g key={tick}><line x1={chart.left} x2={chart.width - chart.right} y1={yy} y2={yy} stroke="#e3e8ef" /><text x={chart.left - 7} y={yy + 3} textAnchor="end" style={labelStyle}>{`1e${tick.toFixed(0)}`}</text></g>
      })}
      <polyline points={line} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinejoin="round" />
      {valid.map(point => <circle key={`${point.snr_db}-${point.frames}`} cx={x(point.snr_db)} cy={y(Number(point.ber ?? 0))} r="3.5" fill="#2563eb" stroke="#fff" strokeWidth="1.5"><title>{`${point.snr_db} dB: BER ${point.ber ?? 0}`}</title></circle>)}
      <text x={chart.width / 2} y={chart.height - 5} textAnchor="middle" style={labelStyle}>SNR (dB)</text>
      <text x="11" y={chart.height / 2} textAnchor="middle" transform={`rotate(-90 11 ${chart.height / 2})`} style={labelStyle}>BER (log)</text>
      <text x={chart.left} y={chart.height - 17} textAnchor="middle" style={labelStyle}>{minX.toFixed(1)}</text>
      <text x={chart.width - chart.right} y={chart.height - 17} textAnchor="middle" style={labelStyle}>{maxX.toFixed(1)}</text>
    </svg>
    <div className="sink-chart-label">{valid.length} SNR points · {valid[valid.length - 1]?.frames ?? 0} frames at last point</div>
  </div>
}
