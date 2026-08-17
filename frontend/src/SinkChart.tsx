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

function downloadReferenceFile(reference: BerReference) {
  const payload = { format: 'signallab-ber-reference', version: 1, reference }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${reference.name.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '') || 'ber-reference'}.ber.json`
  link.click()
  URL.revokeObjectURL(link.href)
}

async function saveReferenceFile(reference: BerReference) {
  const fileName = `${reference.name.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '') || 'ber-reference'}.ber.json`
  const pickerWindow = window as Window & { showSaveFilePicker?: (options: unknown) => Promise<{ createWritable: () => Promise<{ write: (data: Blob) => Promise<void>; close: () => Promise<void> }> }> }
  if (!pickerWindow.showSaveFilePicker) { downloadReferenceFile(reference); return }
  const handle = await pickerWindow.showSaveFilePicker({
    suggestedName: fileName,
    types: [{ description: 'SignalLab BER reference', accept: { 'application/json': ['.ber.json', '.json'] } }],
  })
  const writable = await handle.createWritable()
  const payload = { format: 'signallab-ber-reference', version: 1, reference }
  await writable.write(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
  await writable.close()
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
  const referenceFileRef = useRef<HTMLInputElement>(null)
  const [notice, setNotice] = useState('')
  const [curveName, setCurveName] = useState('Current run')
  const [curveColor, setCurveColor] = useState('#2563eb')
  const [curveStyle, setCurveStyle] = useState<BerLineStyle>('solid')
  const [references, setReferences] = useState<BerReference[]>([])
  const [visibleReferenceIds, setVisibleReferenceIds] = useState<string[]>([])
  const [selectedCurveId, setSelectedCurveId] = useState('current')
  const [editedCurrentPoints, setEditedCurrentPoints] = useState<SinkPoint[]>(points)
  const [detailsOpen, setDetailsOpen] = useState(false)

  useEffect(() => {
    const syncReferences = () => setReferences(readReferences())
    syncReferences()
    window.addEventListener('signallab-ber-reference-change', syncReferences)
    return () => window.removeEventListener('signallab-ber-reference-change', syncReferences)
  }, [])
  useEffect(() => { setEditedCurrentPoints(points) }, [points])

  const activeReferences = references.filter(reference => visibleReferenceIds.includes(reference.id))
  const current = plottedPoints(editedCurrentPoints)
  const selectedReference = selectedCurveId === 'current' ? null : references.find(reference => reference.id === selectedCurveId)
  const selectedCurve = selectedReference || { name: curveName, color: curveColor, style: curveStyle }
  const selectedPoints = selectedReference?.points || editedCurrentPoints
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

  const updateSelectedCurve = (patch: Partial<Pick<BerReference, 'name' | 'color' | 'style'>>) => {
    if (selectedCurveId === 'current') {
      if (patch.name !== undefined) setCurveName(patch.name)
      if (patch.color !== undefined) setCurveColor(patch.color)
      if (patch.style !== undefined) setCurveStyle(patch.style)
      return
    }
    const next = references.map(reference => reference.id === selectedCurveId ? { ...reference, ...patch } : reference)
    setReferences(next)
    persistReferences(next)
  }

  const saveSelectedReference = async () => {
    let reference: BerReference | null = selectedReference ? { ...selectedReference, points: selectedReference.points.map(point => ({ ...point })) } : null
    if (!reference && current.valid.length) {
      reference = {
        id: `ber-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        name: curveName.trim() || `Reference ${references.length + 1}`,
        color: curveColor,
        style: curveStyle,
        points: current.valid.map(point => ({ ...point })),
        createdAt: new Date().toISOString(),
      }
      const next = [...references, reference]
      setReferences(next)
      setVisibleReferenceIds(ids => [...ids, reference!.id])
      setSelectedCurveId(reference.id)
      persistReferences(next)
    }
    if (!reference) return
    try {
      await saveReferenceFile(reference)
    } catch (error) {
      if ((error as DOMException).name !== 'AbortError') setNotice((error as Error).message || 'Could not save BER reference file.')
      return
    }
    setNotice(`Saved file “${reference.name}”`)
  }

  const loadReferenceFile = async (file?: File) => {
    if (!file) return
    try {
      const parsed = JSON.parse(await file.text())
      const candidates = Array.isArray(parsed) ? parsed : [parsed.reference || parsed]
      const imported = candidates.filter(item => item && typeof item.name === 'string' && Array.isArray(item.points) && item.points.length > 0).map(item => ({
        id: `ber-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: item.name,
        color: typeof item.color === 'string' ? item.color : '#d26782',
        style: lineStyles.some(option => option.value === item.style) ? item.style : 'dash',
        points: item.points,
        createdAt: typeof item.createdAt === 'string' ? item.createdAt : new Date().toISOString(),
      } as BerReference))
      if (!imported.length) throw new Error('No valid BER reference found in this file.')
      const next = [...references, ...imported]
      setReferences(next)
      setVisibleReferenceIds(ids => [...ids, ...imported.map(reference => reference.id)])
      setSelectedCurveId(imported[0].id)
      persistReferences(next)
      setNotice(`Loaded ${imported.length} reference file${imported.length > 1 ? 's' : ''}`)
    } catch (error) { setNotice((error as Error).message || 'Could not load BER reference file.') }
  }

  const removeReference = (id: string) => setVisibleReferenceIds(ids => ids.filter(value => value !== id))

  const deleteReference = (id: string) => {
    const next = references.filter(reference => reference.id !== id)
    setReferences(next)
    setVisibleReferenceIds(ids => ids.filter(value => value !== id))
    if (selectedCurveId === id) setSelectedCurveId('current')
    persistReferences(next)
    setNotice('Reference deleted')
  }

  const updateSelectedPoint = (index: number, field: keyof SinkPoint, value: number | null) => {
    const nextPoints = selectedPoints.map((point, pointIndex) => pointIndex === index ? { ...point, [field]: value } : point)
    if (selectedCurveId === 'current') {
      setEditedCurrentPoints(nextPoints)
    } else {
      const next = references.map(reference => reference.id === selectedCurveId ? { ...reference, points: nextPoints } : reference)
      setReferences(next)
      persistReferences(next)
    }
  }

  const addSelectedPoint = () => {
    const last = selectedPoints[selectedPoints.length - 1]
    const nextPoint: SinkPoint = { snr_db: last ? last.snr_db + 1 : 0, bit_errors: 0, total_bits: last?.total_bits || 1, frames: last?.frames || 1, ber: 0 }
    const nextPoints = [...selectedPoints, nextPoint]
    if (selectedCurveId === 'current') setEditedCurrentPoints(nextPoints)
    else {
      const next = references.map(reference => reference.id === selectedCurveId ? { ...reference, points: nextPoints } : reference)
      setReferences(next)
      persistReferences(next)
    }
  }

  const removeSelectedPoint = (index: number) => {
    const nextPoints = selectedPoints.filter((_, pointIndex) => pointIndex !== index)
    if (selectedCurveId === 'current') setEditedCurrentPoints(nextPoints)
    else {
      const next = references.map(reference => reference.id === selectedCurveId ? { ...reference, points: nextPoints } : reference)
      setReferences(next)
      persistReferences(next)
    }
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
    <div className="sink-chart-toolbar"><div className="sink-chart-title">BER vs SNR {live && <span className="live-badge">LIVE</span>}</div><div className="chart-actions"><button onClick={() => exportImage(true)} title="Copy chart as PNG" aria-label="Copy chart as PNG">Copy</button><button onClick={() => exportImage(false)} title="Export chart as PNG" aria-label="Export chart as PNG">PNG</button><button onClick={() => setDetailsOpen(true)} title="Open detailed BER report" aria-label="Open detailed BER report">Details</button></div></div>
    <div className="ber-curve-controls" title="Choose a BER curve, then edit its name and style">
      <select className="ber-curve-select" value={selectedCurveId} onChange={event => { const id = event.target.value; setSelectedCurveId(id); if (id !== 'current') setVisibleReferenceIds(ids => ids.includes(id) ? ids : [...ids, id]) }} aria-label="Select BER curve to edit"><option value="current">Current run</option>{references.map(reference => <option key={reference.id} value={reference.id}>{reference.name}</option>)}</select>
      <div className="ber-curve-editor-row">
        <input className="ber-curve-name" value={selectedCurve.name} onChange={event => updateSelectedCurve({ name: event.target.value })} aria-label="BER curve name" placeholder="Curve name" />
        <input className="ber-color-input" type="color" value={selectedCurve.color} onChange={event => updateSelectedCurve({ color: event.target.value })} aria-label="BER curve color" />
        <select value={selectedCurve.style} onChange={event => updateSelectedCurve({ style: event.target.value as BerLineStyle })} aria-label="BER curve style">{lineStyles.map(style => <option key={style.value} value={style.value}>{style.label}</option>)}</select>
        <button className="ber-save" onClick={() => void saveSelectedReference()} disabled={selectedCurveId === 'current' && !current.valid.length} title="Save selected BER curve as a JSON file">Save .BER</button>
        <button className="ber-load" onClick={() => referenceFileRef.current?.click()} title="Browse for a BER reference JSON file" aria-label="Browse BER reference file">Browse file</button>
        <input ref={referenceFileRef} type="file" accept=".json,.ber.json,application/json" hidden onChange={event => { void loadReferenceFile(event.target.files?.[0]); event.target.value = '' }} />
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
    {detailsOpen && <div className="ber-report-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setDetailsOpen(false) }}>
      <div className="ber-report" role="dialog" aria-modal="true" aria-label="BER details report">
        <div className="ber-report-header"><div><small>BER REPORT</small><h2>BER vs SNR details</h2></div><button className="ber-report-close" onClick={() => setDetailsOpen(false)} aria-label="Close report">×</button></div>
        <div className="ber-report-layout">
          <aside className="ber-report-curves"><div className="ber-report-section-title">CURVES</div><button className={`ber-report-curve ${selectedCurveId === 'current' ? 'active' : ''}`} onClick={() => setSelectedCurveId('current')}><span className="ber-report-dot" style={{ background: curveColor }} />{curveName || 'Current run'}</button>{references.map(reference => <button key={reference.id} className={`ber-report-curve ${selectedCurveId === reference.id ? 'active' : ''}`} onClick={() => { setSelectedCurveId(reference.id); setVisibleReferenceIds(ids => ids.includes(reference.id) ? ids : [...ids, reference.id]) }}><span className="ber-report-dot" style={{ background: reference.color }} />{reference.name}</button>)}</aside>
          <section className="ber-report-editor">
            <div className="ber-report-editor-controls"><label>Name<input value={selectedCurve.name} onChange={event => updateSelectedCurve({ name: event.target.value })} /></label><label>Color<input type="color" value={selectedCurve.color} onChange={event => updateSelectedCurve({ color: event.target.value })} /></label><label>Style<select value={selectedCurve.style} onChange={event => updateSelectedCurve({ style: event.target.value as BerLineStyle })}>{lineStyles.map(style => <option key={style.value} value={style.value}>{style.label}</option>)}</select></label></div>
            <div className="ber-report-table-head"><strong>{selectedCurve.name || 'Current run'} · {selectedPoints.length} points</strong><button onClick={addSelectedPoint}>+ Add point</button></div>
            <div className="ber-report-table-scroll"><table className="ber-report-table"><thead><tr><th>SNR (dB)</th><th>BER</th><th>Frames</th><th>Errors</th><th /></tr></thead><tbody>{selectedPoints.map((point, index) => <tr key={`${selectedCurveId}-${index}`}><td><input type="number" step="any" value={point.snr_db} onChange={event => updateSelectedPoint(index, 'snr_db', Number(event.target.value))} /></td><td><input type="number" step="any" min="0" max="1" value={point.ber ?? ''} onChange={event => updateSelectedPoint(index, 'ber', event.target.value === '' ? null : Number(event.target.value))} /></td><td><input type="number" min="0" value={point.frames} onChange={event => updateSelectedPoint(index, 'frames', Number(event.target.value))} /></td><td><input type="number" min="0" value={point.bit_errors} onChange={event => updateSelectedPoint(index, 'bit_errors', Number(event.target.value))} /></td><td><button className="ber-report-remove" onClick={() => removeSelectedPoint(index)} aria-label={`Remove point ${index + 1}`}>×</button></td></tr>)}</tbody></table></div>
            <div className="ber-report-footer"><button className="ber-save" onClick={() => void saveSelectedReference()} disabled={selectedCurveId === 'current' && !current.valid.length}>Save selected .BER</button><button className="ber-load" onClick={() => referenceFileRef.current?.click()}>Browse / load .BER</button>{selectedCurveId !== 'current' && <button className="ber-report-delete" onClick={() => deleteReference(selectedCurveId)}>Delete selected</button>}</div>
          </section>
        </div>
      </div>
    </div>}
  </div>
}
