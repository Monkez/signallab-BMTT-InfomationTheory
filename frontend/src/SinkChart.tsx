import { useEffect, useRef, useState, type CSSProperties } from 'react'

export type SinkPoint = {
  snr_db: number
  bit_errors: number
  total_bits: number
  frames: number
  ber: number | null
}

export type BerLineStyle = 'solid' | 'dash' | 'dot' | 'dashdot'

export type BerReference = {
  id: string
  name: string
  color: string
  style: BerLineStyle
  points: SinkPoint[]
  createdAt: string
}

const chart = { width: 340, height: 190, left: 42, right: 12, top: 14, bottom: 30 }
const referenceStorageKey = 'signallab.ber-references.v1'
const lineStyles: Array<{ value: BerLineStyle; label: string; dash: string }> = [
  { value: 'solid', label: 'Solid', dash: '' },
  { value: 'dash', label: 'Dashed', dash: '7 4' },
  { value: 'dot', label: 'Dotted', dash: '2 4' },
  { value: 'dashdot', label: 'Dash-dot', dash: '7 4 2 4' },
]

function styleDash(style: BerLineStyle) { return lineStyles.find(option => option.value === style)?.dash || '' }

function readReferences(): BerReference[] {
  try {
    const raw = window.localStorage.getItem(referenceStorageKey)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(item => item && typeof item.id === 'string' && typeof item.name === 'string' && Array.isArray(item.points))
  } catch { return [] }
}

function writeReferences(references: BerReference[]) {
  try { window.localStorage.setItem(referenceStorageKey, JSON.stringify(references)) } catch { /* storage can be disabled */ }
}

function persistReferences(references: BerReference[]) {
  writeReferences(references)
  window.dispatchEvent(new Event('signallab-ber-reference-change'))
}

async function svgToPng(svg: SVGSVGElement): Promise<Blob> {
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  const source = new XMLSerializer().serializeToString(clone)
  const image = new Image()
  const url = URL.createObjectURL(new Blob([source], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error('Could not render chart image')); image.src = url })
    const scale = 3
    const canvas = document.createElement('canvas')
    canvas.width = chart.width * scale
    canvas.height = chart.height * scale
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas is unavailable')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return await new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Could not encode chart image')), 'image/png'))
  } finally { URL.revokeObjectURL(url) }
}

async function copyPng(blob: Blob) {
  if (!navigator.clipboard || typeof ClipboardItem === 'undefined') throw new Error('Image clipboard is unavailable')
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
}

function plottedPoints(points: SinkPoint[]) {
  const valid = points.filter(point => Number.isFinite(point.snr_db) && point.total_bits > 0)
  const firstZero = valid.findIndex(point => point.ber === 0)
  return { valid, firstZero, plotted: firstZero >= 0 ? valid.slice(0, firstZero + 1) : valid }
}

export function BerChart({ points, live = false }: { points: SinkPoint[]; live?: boolean }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [notice, setNotice] = useState('')
  const [curveName, setCurveName] = useState('Current run')
  const [curveColor, setCurveColor] = useState('#2563eb')
  const [curveStyle, setCurveStyle] = useState<BerLineStyle>('solid')
  const [references, setReferences] = useState<BerReference[]>([])
  const [visibleReferenceIds, setVisibleReferenceIds] = useState<string[]>([])
  const [showReferencePicker, setShowReferencePicker] = useState(false)

  useEffect(() => {
    const syncReferences = () => setReferences(readReferences())
    syncReferences()
    window.addEventListener('signallab-ber-reference-change', syncReferences)
    return () => window.removeEventListener('signallab-ber-reference-change', syncReferences)
  }, [])

  const activeReferences = references.filter(reference => visibleReferenceIds.includes(reference.id))
  const current = plottedPoints(points)
  const curves = [
    { id: 'current', name: curveName.trim() || 'Current run', color: curveColor, style: curveStyle, ...current },
    ...activeReferences.map(reference => ({ id: reference.id, name: reference.name, color: reference.color, style: reference.style, ...plottedPoints(reference.points) })),
  ].filter(curve => curve.valid.length > 0)

  if (!curves.length) return <div className="sink-chart empty">Run an experiment to see BER vs SNR.</div>

  const allValid = curves.flatMap(curve => curve.valid)
  const minX = Math.min(...allValid.map(point => point.snr_db))
  const maxX = Math.max(...allValid.map(point => point.snr_db))
  const xRange = Math.max(maxX - minX, 1)
  const values = curves.flatMap(curve => curve.plotted.map(point => Math.max(Number(point.ber ?? 0), 1e-8)))
  const maxLog = Math.ceil(Math.max(...values.map(value => Math.log10(value)), -1))
  const minLog = Math.min(-8, Math.floor(Math.min(...values.map(value => Math.log10(value)))))
  const yRange = Math.max(maxLog - minLog, 1)
  const x = (value: number) => chart.left + ((value - minX) / xRange) * (chart.width - chart.left - chart.right)
  const y = (value: number) => chart.top + ((maxLog - Math.log10(Math.max(value, 1e-8))) / yRange) * (chart.height - chart.top - chart.bottom)
  const lineFor = (curve: typeof curves[number]) => {
    const linePoints: string[] = []
    const linePlotted = curve.firstZero >= 0 ? curve.plotted.slice(0, curve.firstZero) : curve.plotted
    linePlotted.forEach(point => linePoints.push(`${x(point.snr_db)},${y(Number(point.ber ?? 0))}`))
    if (curve.firstZero > 0 && linePlotted.length) linePoints.push(`${x(linePlotted[linePlotted.length - 1].snr_db)},${y(0)}`)
    return linePoints.join(' ')
  }
  const labelStyle: CSSProperties = { fontSize: 9, fill: '#6b7788' }
  const yTicks = [0, 1, 2, 3].map(index => maxLog - (index * yRange) / 3)

  const saveReference = () => {
    if (!current.valid.length) return
    const reference: BerReference = {
      id: `ber-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: curveName.trim() || `Reference ${references.length + 1}`,
      color: curveColor,
      style: curveStyle,
      points: current.valid.map(point => ({ ...point })),
      createdAt: new Date().toISOString(),
    }
    const next = [...references, reference]
    setReferences(next)
    setVisibleReferenceIds(ids => [...ids, reference.id])
    persistReferences(next)
    setNotice(`Saved “${reference.name}”`)
  }

  const loadReference = (id: string) => {
    if (!id) return
    setVisibleReferenceIds(ids => ids.includes(id) ? ids : [...ids, id])
    setNotice(`Loaded “${references.find(reference => reference.id === id)?.name || 'reference'}”`)
  }

  const removeReference = (id: string) => setVisibleReferenceIds(ids => ids.filter(value => value !== id))

  const deleteReference = (id: string) => {
    const next = references.filter(reference => reference.id !== id)
    setReferences(next)
    setVisibleReferenceIds(ids => ids.filter(value => value !== id))
    persistReferences(next)
    setNotice('Reference deleted')
  }

  const exportImage = async (copy: boolean) => {
    if (!svgRef.current) return
    try {
      const blob = await svgToPng(svgRef.current)
      if (copy) { await copyPng(blob); setNotice('Copied') } else {
        const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'signallab-ber-vs-snr.png'; link.click(); URL.revokeObjectURL(link.href); setNotice('PNG saved')
      }
    } catch (error) { setNotice((error as Error).message) }
    window.setTimeout(() => setNotice(''), 1800)
  }

  return <div className="sink-chart">
    <div className="sink-chart-toolbar"><div className="sink-chart-title">BER vs SNR {live && <span className="live-badge">LIVE</span>}</div><div className="chart-actions"><button onClick={() => exportImage(true)} title="Copy chart as PNG" aria-label="Copy chart as PNG">Copy</button><button onClick={() => exportImage(false)} title="Export chart as PNG" aria-label="Export chart as PNG">PNG</button></div></div>
    <div className="ber-curve-controls" title="Name and style the current BER curve">
      <input className="ber-curve-name" value={curveName} onChange={event => setCurveName(event.target.value)} aria-label="BER curve name" placeholder="Curve name" />
      <input className="ber-color-input" type="color" value={curveColor} onChange={event => setCurveColor(event.target.value)} aria-label="BER curve color" />
      <select value={curveStyle} onChange={event => setCurveStyle(event.target.value as BerLineStyle)} aria-label="BER curve style">{lineStyles.map(style => <option key={style.value} value={style.value}>{style.label}</option>)}</select>
      <button className="ber-save" onClick={saveReference} disabled={!current.valid.length} title="Save current curve as a reusable reference">Save reference</button>
      <div className="ber-reference-loader">
        <button className="ber-load" onClick={() => setShowReferencePicker(value => !value)} disabled={!references.length} title="Choose a saved BER reference" aria-label="Load BER reference">Load reference</button>
        {showReferencePicker && references.length > 0 && <div className="ber-reference-picker">{references.map(reference => <button key={reference.id} onClick={() => { loadReference(reference.id); setShowReferencePicker(false) }}>{reference.name}</button>)}</div>}
      </div>
    </div>
    <svg ref={svgRef} viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Bit error rate versus SNR chart">
      <rect x={chart.left} y={chart.top} width={chart.width - chart.left - chart.right} height={chart.height - chart.top - chart.bottom} fill="#f8fafc" stroke="#d7dee8" />
      {yTicks.map((tick, index) => { const yy = chart.top + (index / 3) * (chart.height - chart.top - chart.bottom); return <g key={tick}><line x1={chart.left} x2={chart.width - chart.right} y1={yy} y2={yy} stroke="#e3e8ef" /><text x={chart.left - 7} y={yy + 3} textAnchor="end" style={labelStyle}>{`1e${tick.toFixed(0)}`}</text></g> })}
      {curves.map((curve, curveIndex) => <g key={curve.id}>
        {lineFor(curve) && <polyline points={lineFor(curve)} fill="none" stroke={curve.color} strokeWidth={curveIndex === 0 ? 2.5 : 2} strokeDasharray={styleDash(curve.style)} strokeLinejoin="round" opacity={curveIndex === 0 ? 1 : 0.86} />}
        {curve.plotted.filter(point => point.ber !== 0).map(point => <circle key={`${curve.id}-${point.snr_db}-${point.frames}`} cx={x(point.snr_db)} cy={y(Number(point.ber ?? 0))} r={curveIndex === 0 ? 3.5 : 3} fill={curve.color} stroke="#fff" strokeWidth="1.5"><title>{`${curve.name} · ${point.snr_db} dB: BER ${point.ber ?? 0}`}</title></circle>)}
      </g>)}
      <text x={chart.width / 2} y={chart.height - 5} textAnchor="middle" style={labelStyle}>SNR (dB)</text><text x="11" y={chart.height / 2} textAnchor="middle" transform={`rotate(-90 11 ${chart.height / 2})`} style={labelStyle}>BER (log)</text><text x={chart.left} y={chart.height - 17} textAnchor="middle" style={labelStyle}>{minX.toFixed(1)}</text><text x={chart.width - chart.right} y={chart.height - 17} textAnchor="middle" style={labelStyle}>{maxX.toFixed(1)}</text>
    </svg>
    <div className="ber-legend" aria-label="BER curve legend">{curves.map((curve, index) => <div className="ber-legend-item" key={curve.id}><span className="ber-legend-swatch" style={{ borderTopColor: curve.color, borderTopStyle: curve.style === 'dot' ? 'dotted' : curve.style === 'dash' || curve.style === 'dashdot' ? 'dashed' : 'solid' }} /><span className="ber-legend-name">{curve.name}</span>{index > 0 && <><button className="ber-legend-action" onClick={() => removeReference(curve.id)} title="Hide reference">Hide</button><button className="ber-legend-delete" onClick={() => deleteReference(curve.id)} title="Delete saved reference">×</button></>}</div>)}</div>
    {notice && <div className="chart-notice">{notice}</div>}
    <div className="sink-chart-label">{current.plotted.length} SNR points plotted · {current.plotted[current.plotted.length - 1]?.frames ?? 0} frames at last point</div>
  </div>
}
