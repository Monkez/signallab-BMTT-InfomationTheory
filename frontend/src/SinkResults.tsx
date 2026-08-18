import { Activity, Gauge, Radio, Waves } from 'lucide-react'
import type { FlowNode } from './types'

type Props = {
  nodes: FlowNode[]
  metrics: Record<string, number>
}

function complexValue(value: string): [number, number] | null {
  const text = value.trim().replaceAll(' ', '').replace(/j$/i, '')
  const match = text.match(/^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)([+-](?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)$/i)
  if (match) return [Number(match[1]), Number(match[2])]
  const scalar = Number(text)
  return Number.isFinite(scalar) ? [scalar, 0] : null
}

function ConstellationPreview({ values }: { values: string[] }) {
  const points = values.map(complexValue).filter((point): point is [number, number] => Boolean(point)).slice(0, 128)
  if (!points.length) return <div className="sink-visual-empty">No complex samples captured.</div>
  const extent = Math.max(1, ...points.flatMap(([i, q]) => [Math.abs(i), Math.abs(q)]))
  const x = (i: number) => 130 + (i / extent) * 105
  const y = (q: number) => 78 - (q / extent) * 62
  return <svg className="constellation-preview" viewBox="0 0 260 96" role="img" aria-label="Constellation preview"><path d="M130 10v68M25 78h210" /><text x="238" y="90">I</text><text x="134" y="12">Q</text>{points.map(([i, q], index) => <circle key={index} cx={x(i)} cy={y(q)} r="2.7" />)}</svg>
}

export function SinkResults({ nodes, metrics }: Props) {
  const sinks = nodes.filter(node => ['power_meter', 'constellation', 'scope', 'source_analyzer', 'ser'].includes(node.data.blockType))
  if (!sinks.length) return null
  const cards = sinks.map(node => {
    const type = node.data.blockType
    const preview = node.data.portPreviews?.inputs?.in
    if (type === 'power_meter' && metrics.power_mean !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Activity size={15} /><strong>{node.data.label}</strong><span>TX power</span></div><div className="sink-result-value">{metrics.power_mean.toExponential(4)}<small>mean power</small></div></div>
    if (type === 'scope' && metrics.scope_mean_amplitude !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Waves size={15} /><strong>{node.data.label}</strong><span>Scope</span></div><div className="sink-result-stats"><b>{metrics.scope_mean_amplitude.toFixed(4)}<small>mean amplitude</small></b><b>{metrics.scope_peak_amplitude?.toFixed(4) ?? '—'}<small>peak</small></b></div></div>
    if (type === 'constellation' && metrics.constellation_mean_i !== undefined) return <div className="sink-result-card constellation-card" key={node.id}><div className="sink-result-heading"><Radio size={15} /><strong>{node.data.label}</strong><span>Constellation</span></div><ConstellationPreview values={preview?.sample || []} /><div className="sink-result-stats"><b>{metrics.constellation_mean_i.toFixed(3)}<small>mean I</small></b><b>{metrics.constellation_mean_q.toFixed(3)}<small>mean Q</small></b><b>{metrics.constellation_mean_power.toFixed(4)}<small>mean |x|</small></b></div></div>
    if (type === 'source_analyzer' && metrics.source_entropy !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Activity size={15} /><strong>{node.data.label}</strong><span>Source theory</span></div><div className="sink-result-stats"><b>{metrics.source_entropy.toFixed(4)}<small>H(X)</small></b><b>{metrics.source_efficiency_percent.toFixed(2)}%<small>efficiency</small></b></div></div>
    if (type === 'ser' && metrics.ser !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Gauge size={15} /><strong>{node.data.label}</strong><span>Symbol error rate</span></div><div className="sink-result-value">{metrics.ser.toExponential(4)}<small>{metrics.symbol_errors} / {metrics.total_symbols} errors</small></div></div>
    return null
  }).filter(Boolean)
  return cards.length ? <div className="sink-results"><div className="sink-results-title">SINK RESULTS <span>{cards.length} active</span></div><div className="sink-results-grid">{cards}</div></div> : null
}
