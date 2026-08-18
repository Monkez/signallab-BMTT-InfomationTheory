import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Activity, Gauge, Radio, Waves, X } from 'lucide-react'
import type { FlowNode } from './types'
import type { SinkPoint } from './features/ber/types'
import { BerChart } from './SinkChart'
import { ResultsTable } from './ResultsTable'

type SinkKind = 'power_meter' | 'constellation' | 'scope' | 'source_analyzer' | 'ser'
type SinkReference = { id: string; name: string; kind: SinkKind; color: string; style: 'bars' | 'line' | 'dots'; metrics: Record<string, number>; samples: string[]; createdAt: string }
type Props = { nodes: FlowNode[]; metrics: Record<string, number>; berPoints?: SinkPoint[]; berLive?: boolean }

const referenceKey = (nodeId: string) => `signallab:sink-references:${nodeId}`
const readReferences = (nodeId: string): SinkReference[] => { try { const value = JSON.parse(localStorage.getItem(referenceKey(nodeId)) || '[]'); return Array.isArray(value) ? value : [] } catch { return [] } }
const saveReferences = (nodeId: string, references: SinkReference[]) => localStorage.setItem(referenceKey(nodeId), JSON.stringify(references))

function complexValue(value: string): [number, number] | null {
  const text = value.trim().replaceAll(' ', '').replace(/j$/i, '')
  const match = text.match(/^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)([+-](?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)$/i)
  if (match) return [Number(match[1]), Number(match[2])]
  const scalar = Number(text)
  return Number.isFinite(scalar) ? [scalar, 0] : null
}

function ConstellationPreview({ values, large = false, color = '#2d6be4' }: { values: string[]; large?: boolean; color?: string }) {
  const points = values.map(complexValue).filter((point): point is [number, number] => Boolean(point)).slice(0, 512)
  if (!points.length) return <div className="sink-visual-empty">No complex samples captured.</div>
  const extent = Math.max(1, ...points.flatMap(([i, q]) => [Math.abs(i), Math.abs(q)]))
  const x = (i: number) => 150 + (i / extent) * 125
  const y = (q: number) => 90 - (q / extent) * 72
  return <svg className={`constellation-preview ${large ? 'large' : ''}`} viewBox="0 0 300 108" role="img" aria-label="Constellation preview"><path d="M150 12v78M25 90h250" /><text x="280" y="102">I</text><text x="154" y="13">Q</text>{points.map(([i, q], index) => <circle key={index} cx={x(i)} cy={y(q)} r={large ? 3 : 2.7} style={{ fill: color }} />)}</svg>
}

const iconFor = (kind: SinkKind) => kind === 'constellation' ? Radio : kind === 'scope' ? Waves : kind === 'ser' ? Gauge : Activity
const titleFor = (kind: SinkKind) => ({ power_meter: 'TX Power', constellation: 'Constellation', scope: 'Scope', source_analyzer: 'Source theory', ser: 'Symbol error rate' })[kind]

export function SinkResults({ nodes, metrics, berPoints = [], berLive = false }: Props) {
  const hasBer = nodes.some(node => node.data.blockType === 'ber') && berPoints.length > 0
  const sinks = nodes.filter(node => ['ber', 'power_meter', 'constellation', 'scope', 'source_analyzer', 'ser'].includes(node.data.blockType)) as FlowNode[]
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null)
  const activeNode = sinks.find(node => node.id === detailNodeId) || null
  if (!sinks.length) return null
  const cards = sinks.map(node => {
    const type = node.data.blockType as SinkKind
    const preview = node.data.portPreviews?.inputs?.in
    const Icon = iconFor(type)
    const detail = <button className="sink-detail-button" onClick={() => setDetailNodeId(node.id)}>Details</button>
    if (type === 'power_meter' && metrics.power_mean !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Icon size={15} /><strong>{node.data.label}</strong><span>TX power</span></div><div className="sink-result-value">{metrics.power_mean.toExponential(4)}<small>mean power</small></div>{detail}</div>
    if (type === 'scope' && metrics.scope_mean_amplitude !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Icon size={15} /><strong>{node.data.label}</strong><span>Scope</span></div><div className="sink-result-stats"><b>{metrics.scope_mean_amplitude.toFixed(4)}<small>mean amplitude</small></b><b>{metrics.scope_peak_amplitude?.toFixed(4) ?? '—'}<small>peak</small></b></div>{detail}</div>
    if (type === 'constellation' && metrics.constellation_mean_i !== undefined) return <div className="sink-result-card constellation-card" key={node.id}><div className="sink-result-heading"><Icon size={15} /><strong>{node.data.label}</strong><span>Constellation</span></div><ConstellationPreview values={preview?.sample || []} /><div className="sink-result-stats"><b>{metrics.constellation_mean_i.toFixed(3)}<small>mean I</small></b><b>{metrics.constellation_mean_q.toFixed(3)}<small>mean Q</small></b><b>{metrics.constellation_mean_power.toFixed(4)}<small>mean |x|</small></b></div>{detail}</div>
    if (type === 'source_analyzer' && metrics.source_entropy !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Icon size={15} /><strong>{node.data.label}</strong><span>Source theory</span></div><div className="sink-result-stats"><b>{metrics.source_entropy.toFixed(4)}<small>H(X)</small></b><b>{metrics.source_efficiency_percent.toFixed(2)}%<small>efficiency</small></b></div>{detail}</div>
    if (type === 'ser' && metrics.ser !== undefined) return <div className="sink-result-card" key={node.id}><div className="sink-result-heading"><Icon size={15} /><strong>{node.data.label}</strong><span>Symbol error rate</span></div><div className="sink-result-value">{metrics.ser.toExponential(4)}<small>{metrics.symbol_errors} / {metrics.total_symbols} errors</small></div>{detail}</div>
    return null
  }).filter(Boolean)
  return <>{(cards.length || hasBer) ? <div className="sink-results"><div className="sink-results-title">SINK RESULTS <span>{cards.length + (hasBer ? 1 : 0)} active</span></div>{hasBer && <div className="sink-ber-card"><div className="sink-result-heading"><Gauge size={15} /><strong>BER Meter</strong><span>BER vs SNR</span></div><BerChart points={berPoints} live={berLive} /><ResultsTable points={berPoints} /></div>}<div className="sink-results-grid">{cards}</div></div> : null}{activeNode && <SinkDetail node={activeNode} metrics={metrics} onClose={() => setDetailNodeId(null)} />}</>
}

function SinkDetail({ node, metrics, onClose }: { node: FlowNode; metrics: Record<string, number>; onClose: () => void }) {
  const kind = node.data.blockType as SinkKind
  const currentSamples = node.data.portPreviews?.inputs?.in?.sample || []
  const currentMetrics = useMemo(() => Object.fromEntries(Object.entries(metrics).filter(([key]) => key.startsWith(kind === 'power_meter' ? 'power_' : kind === 'constellation' ? 'constellation_' : kind === 'scope' ? 'scope_' : kind === 'source_analyzer' ? 'source_' : 'ser') || (kind === 'ser' && ['ser', 'symbol_errors', 'total_symbols'].includes(key)))), [kind, metrics])
  const [tab, setTab] = useState<'chart' | 'edit' | 'references'>('chart')
  const [name, setName] = useState(node.data.label)
  const [color, setColor] = useState('#2563eb')
  const [style, setStyle] = useState<SinkReference['style']>('line')
  const [editedMetrics, setEditedMetrics] = useState<Record<string, number>>(currentMetrics)
  const [references, setReferences] = useState<SinkReference[]>([])
  const [selectedReferenceId, setSelectedReferenceId] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const selected = references.find(reference => reference.id === selectedReferenceId)
  const displayMetrics = selected?.metrics || editedMetrics
  const displaySamples = selected?.samples || currentSamples
  useEffect(() => { setReferences(readReferences(node.id)) }, [node.id])
  useEffect(() => { setEditedMetrics(currentMetrics) }, [currentMetrics])
  const makeReference = (): SinkReference => ({ id: `${kind}-${Date.now()}`, name: name.trim() || `${titleFor(kind)} reference`, kind, color, style, metrics: { ...editedMetrics }, samples: [...currentSamples], createdAt: new Date().toISOString() })
  const persist = (next: SinkReference[]) => { setReferences(next); saveReferences(node.id, next) }
  const saveReferenceFile = (reference: SinkReference) => { const blob = new Blob([JSON.stringify(reference, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${reference.name.replace(/[^a-z0-9_-]+/gi, '_')}.${kind}.json`; link.click(); URL.revokeObjectURL(link.href); setNotice('Reference saved') }
  const save = () => { const reference = selected ? { ...selected, name, color, style, metrics: { ...editedMetrics } } : makeReference(); const next = selected ? references.map(item => item.id === selected.id ? reference : item) : [...references, reference]; persist(next); setSelectedReferenceId(reference.id); setNotice('Reference saved') }
  const load = (file?: File) => { if (!file) return; const reader = new FileReader(); reader.onload = () => { try { const value = JSON.parse(String(reader.result)); if (value.kind !== kind || !value.metrics) throw new Error('Reference belongs to another sink type'); const reference = { ...value, id: `${kind}-${Date.now()}` } as SinkReference; persist([...references, reference]); setSelectedReferenceId(reference.id); setName(reference.name); setColor(reference.color); setStyle(reference.style); setNotice('Reference loaded') } catch (error) { setNotice((error as Error).message) } }; reader.readAsText(file) }
  const Icon = iconFor(kind)
  return createPortal(<div className="sink-detail-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}><section className="sink-detail" role="dialog" aria-modal="true"><header className="sink-detail-header"><div><small>SINK REPORT</small><h2>{name} details</h2></div><button onClick={onClose} aria-label="Close details"><X size={20} /></button></header><nav className="sink-detail-tabs"><button className={tab === 'chart' ? 'active' : ''} onClick={() => setTab('chart')}>Chart</button><button className={tab === 'edit' ? 'active' : ''} onClick={() => setTab('edit')}>Edit &amp; Data</button><button className={tab === 'references' ? 'active' : ''} onClick={() => setTab('references')}>References</button></nav>{tab === 'chart' && <div className="sink-detail-chart"><div className="sink-detail-title"><Icon size={18} /><strong>{titleFor(kind)}</strong><span>{selected ? `Reference: ${selected.name}` : 'Current run'}</span></div>{kind === 'constellation' ? <ConstellationPreview values={displaySamples} large color={selected?.color || color} /> : <div className="sink-detail-metric-grid">{Object.entries(displayMetrics).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{typeof value === 'number' ? value.toExponential(6) : value}</strong></div>)}</div>}<p className="sink-detail-note">This report is tied to the selected sink. Use Edit &amp; Data for presentation parameters and References to compare or archive additional runs.</p></div>}{tab === 'edit' && <div className="sink-detail-edit"><div className="sink-edit-grid"><label>Name<input value={name} onChange={event => setName(event.target.value)} /></label><label>Color<input type="color" value={color} onChange={event => setColor(event.target.value)} /></label><label>Style<select value={style} onChange={event => setStyle(event.target.value as SinkReference['style'])}><option value="line">Line</option><option value="bars">Bars</option><option value="dots">Dots</option></select></label></div><h3>Metrics</h3><div className="sink-metric-editor">{Object.entries(editedMetrics).map(([key, value]) => <label key={key}>{key.replaceAll('_', ' ')}<input type="number" step="any" value={value} onChange={event => setEditedMetrics(current => ({ ...current, [key]: Number(event.target.value) }))} /></label>)}</div><h3>Captured samples</h3><textarea className="sink-sample-editor" value={displaySamples.join('\n')} readOnly /><div className="sink-detail-actions"><button onClick={save}>Save reference</button><button onClick={() => saveReferenceFile(selected || makeReference())}>Export JSON</button></div></div>}{tab === 'references' && <div className="sink-reference-editor"><div className="sink-reference-toolbar"><button onClick={() => save()}>Save current</button><label className="sink-load-button">Browse / Load<input type="file" accept="application/json,.json" hidden onChange={event => { load(event.target.files?.[0]); event.target.value = '' }} /></label></div>{references.length ? <div className="sink-reference-list">{references.map(reference => <button className={selectedReferenceId === reference.id ? 'active' : ''} key={reference.id} onClick={() => { setSelectedReferenceId(reference.id); setName(reference.name); setColor(reference.color); setStyle(reference.style); setEditedMetrics(reference.metrics) }}><span style={{ background: reference.color }} />{reference.name}<small>{new Date(reference.createdAt).toLocaleString()}</small></button>)}</div> : <p className="sink-detail-empty">No saved references for this sink.</p>}{selected && <div className="sink-reference-footer"><button onClick={() => saveReferenceFile(selected)}>Export selected</button><button onClick={() => { persist(references.filter(reference => reference.id !== selected.id)); setSelectedReferenceId(null); setNotice('Reference deleted') }}>Delete selected</button></div>}</div>}{notice && <div className="sink-detail-notice">{notice}</div>}</section></div>, document.body)
}
