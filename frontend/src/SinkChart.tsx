import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { BerLegend } from './features/ber/BerLegend'
import { BerPlot } from './features/ber/BerPlot'
import { plottedPoints } from './features/ber/chartMath'
import { lineStyles } from './features/ber/constants'
import { copyPng, svgToPng } from './features/ber/imageExport'
import { parseReferenceFile, saveReferenceFile } from './features/ber/referenceFiles'
import { persistReferences, readReferences, referenceChangeEvent } from './features/ber/referenceStore'
import type { BerCurve, BerLineStyle, BerReference, SinkPoint } from './features/ber/types'

export type { BerLineStyle, BerReference, SinkPoint } from './features/ber/types'

export function BerChart({ points, live = false }: { points: SinkPoint[]; live?: boolean }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const reportSvgRef = useRef<SVGSVGElement>(null)
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
  const [detailsTab, setDetailsTab] = useState<'chart' | 'edit'>('chart')

  useEffect(() => {
    const syncReferences = () => setReferences(readReferences())
    syncReferences()
    window.addEventListener(referenceChangeEvent, syncReferences)
    return () => window.removeEventListener(referenceChangeEvent, syncReferences)
  }, [])
  useEffect(() => { setEditedCurrentPoints(points) }, [points])

  const activeReferences = references.filter(reference => visibleReferenceIds.includes(reference.id))
  const current = plottedPoints(editedCurrentPoints)
  const selectedReference = selectedCurveId === 'current' ? null : references.find(reference => reference.id === selectedCurveId)
  const selectedCurve = selectedReference || { name: curveName, color: curveColor, style: curveStyle }
  const selectedPoints = selectedReference?.points || editedCurrentPoints
  const curves: BerCurve[] = [
    { id: 'current', name: curveName.trim() || 'Current run', color: curveColor, style: curveStyle, ...current },
    ...activeReferences.map(reference => ({ id: reference.id, name: reference.name, color: reference.color, style: reference.style, ...plottedPoints(reference.points) })),
  ].filter(curve => curve.valid.length > 0)

  if (!curves.length) return <div className="sink-chart empty">Run an experiment to see BER vs SNR.</div>

  const allValid = curves.flatMap(curve => curve.valid)

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
      const imported = await parseReferenceFile(file)
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
    <div className="sink-chart-toolbar"><div className="sink-chart-title">BER vs SNR {live && <span className="live-badge">LIVE</span>}</div><div className="chart-actions"><button onClick={() => exportImage(true)} title="Copy chart as PNG" aria-label="Copy chart as PNG">Copy</button><button onClick={() => exportImage(false)} title="Export chart as PNG" aria-label="Export chart as PNG">PNG</button><button onClick={() => { setDetailsTab('chart'); setDetailsOpen(true) }} title="Open detailed BER report" aria-label="Open detailed BER report">Details</button></div></div>
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
    <BerPlot ref={svgRef} curves={curves} />
    <BerLegend curves={curves} onHide={removeReference} onDelete={deleteReference} />
    {notice && <div className="chart-notice">{notice}</div>}
    <div className="sink-chart-label">{current.plotted.length} SNR points plotted · {current.plotted[current.plotted.length - 1]?.frames ?? 0} frames at last point</div>
    {detailsOpen && createPortal(<div className="ber-report-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setDetailsOpen(false) }}>
      <div className="ber-report" role="dialog" aria-modal="true" aria-label="BER details report">
        <div className="ber-report-header"><div><small>BER REPORT</small><h2>BER vs SNR details</h2></div><button className="ber-report-close" onClick={() => setDetailsOpen(false)} aria-label="Close report">×</button></div>
        <div className="ber-report-tabs"><button className={detailsTab === 'chart' ? 'active' : ''} onClick={() => setDetailsTab('chart')}>Chart</button><button className={detailsTab === 'edit' ? 'active' : ''} onClick={() => setDetailsTab('edit')}>Edit &amp; Data</button></div>
        {detailsTab === 'chart' ? <div className="ber-report-chart-wrap primary"><div className="ber-report-chart-title"><strong>BER vs SNR</strong><span>{curves.length} curve{curves.length === 1 ? '' : 's'} · {allValid.length} measured points</span></div><BerLegend curves={curves} variant="report" /><BerPlot ref={reportSvgRef} curves={curves} variant="report" /></div> :
        <div className="ber-report-layout">
          <aside className="ber-report-curves"><div className="ber-report-section-title">CURVES</div><button className={`ber-report-curve ${selectedCurveId === 'current' ? 'active' : ''}`} onClick={() => setSelectedCurveId('current')}><span className="ber-report-dot" style={{ background: curveColor }} />{curveName || 'Current run'}</button>{references.map(reference => <button key={reference.id} className={`ber-report-curve ${selectedCurveId === reference.id ? 'active' : ''}`} onClick={() => { setSelectedCurveId(reference.id); setVisibleReferenceIds(ids => ids.includes(reference.id) ? ids : [...ids, reference.id]) }}><span className="ber-report-dot" style={{ background: reference.color }} />{reference.name}</button>)}</aside>
          <section className="ber-report-editor">
            <div className="ber-report-editor-controls"><label>Name<input value={selectedCurve.name} onChange={event => updateSelectedCurve({ name: event.target.value })} /></label><label>Color<input type="color" value={selectedCurve.color} onChange={event => updateSelectedCurve({ color: event.target.value })} /></label><label>Style<select value={selectedCurve.style} onChange={event => updateSelectedCurve({ style: event.target.value as BerLineStyle })}>{lineStyles.map(style => <option key={style.value} value={style.value}>{style.label}</option>)}</select></label></div>
            <div className="ber-report-table-head"><strong>{selectedCurve.name || 'Current run'} · {selectedPoints.length} points</strong><button onClick={addSelectedPoint}>+ Add point</button></div>
            <div className="ber-report-table-scroll"><table className="ber-report-table"><thead><tr><th>SNR (dB)</th><th>BER</th><th>Frames</th><th>Errors</th><th /></tr></thead><tbody>{selectedPoints.map((point, index) => <tr key={`${selectedCurveId}-${index}`}><td><input type="number" step="any" value={point.snr_db} onChange={event => updateSelectedPoint(index, 'snr_db', Number(event.target.value))} /></td><td><input type="number" step="any" min="0" max="1" value={point.ber ?? ''} onChange={event => updateSelectedPoint(index, 'ber', event.target.value === '' ? null : Number(event.target.value))} /></td><td><input type="number" min="0" value={point.frames} onChange={event => updateSelectedPoint(index, 'frames', Number(event.target.value))} /></td><td><input type="number" min="0" value={point.bit_errors} onChange={event => updateSelectedPoint(index, 'bit_errors', Number(event.target.value))} /></td><td><button className="ber-report-remove" onClick={() => removeSelectedPoint(index)} aria-label={`Remove point ${index + 1}`}>×</button></td></tr>)}</tbody></table></div>
            <div className="ber-report-footer"><button className="ber-save" onClick={() => void saveSelectedReference()} disabled={selectedCurveId === 'current' && !current.valid.length}>Save selected .BER</button><button className="ber-load" onClick={() => referenceFileRef.current?.click()}>Browse / load .BER</button>{selectedCurveId !== 'current' && <button className="ber-report-delete" onClick={() => deleteReference(selectedCurveId)}>Delete selected</button>}</div>
          </section>
        </div>}
      </div>
    </div>, document.body)}
  </div>
}
