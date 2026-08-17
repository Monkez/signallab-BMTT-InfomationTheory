import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState,
  BackgroundVariant, MarkerType, type Connection, type NodeMouseHandler, type OnNodeDrag,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Activity, ArrowLeftRight, Box, Braces, CircleStop, Download,
  Layers3, PanelBottom, PanelLeft, PanelRight, Play, Plus, RotateCcw, Search, Terminal, Trash2, Upload, X,
} from 'lucide-react'
import { SignalNode } from './SignalNode'
import { cancelJob, createJob, getJob, graphPayload } from './api'
import { initialEdges, initialNodes, pythonTemplate } from './sample'
import type { BlockSpec, FlowNode, Job, SimulationConfig } from './types'
import { BerChart } from './SinkChart'
import { ResultsTable } from './ResultsTable'
import { FlowMiniMapNode } from './components/FlowMiniMapNode'
import { fallbackSpecs, iconFor, miniMapColor } from './features/blocks/catalog'
import { defaultSimulationConfig, snrPointCount } from './features/experiment/config'

const formatNumber = (n: number) => new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(n)
type ConsoleLevel = 'info' | 'success' | 'warning' | 'error'
type ConsoleEntry = { id: number; time: string; level: ConsoleLevel; message: string }

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [specs, setSpecs] = useState<BlockSpec[]>(fallbackSpecs)
  const [selectedId, setSelectedId] = useState<string | null>('channel')
  const [search, setSearch] = useState('')
  const [config, setConfig] = useState<SimulationConfig>(defaultSimulationConfig)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [rightTab, setRightTab] = useState<'block' | 'run'>('run')
  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)
  const [leftWidth, setLeftWidth] = useState(270)
  const [rightWidth, setRightWidth] = useState(360)
  const [consoleOpen, setConsoleOpen] = useState(true)
  const [consoleHeight, setConsoleHeight] = useState(156)
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const bootLoggedRef = useRef(false)
  const lastSnrRef = useRef<number | null>(null)
  const consoleResizeRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const resizeRef = useRef<{ side: 'left' | 'right'; startX: number; startWidth: number } | null>(null)
  const selected = nodes.find(n => n.id === selectedId)
  const visibleParams = selected ? Object.entries(selected.data.params).filter(([key]) => {
    if (key === 'data_base64' || key === 'file_name') return false
    if (selected.data.blockType === 'awgn' && (key === 'snr_mode' || key === 'ebn0_db')) return false
    if (selected.data.blockType === 'image_file_source' && key === 'mode') return false
    return true
  }) : []
  const appendLog = useCallback((level: ConsoleLevel, message: string) => {
    setConsoleEntries(entries => [...entries.slice(-199), { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), level, message }])
  }, [])

  useEffect(() => {
    if (bootLoggedRef.current) return
    bootLoggedRef.current = true
    appendLog('info', 'SignalLab ready · build the graph, then run an experiment.')
    fetch('/api/blocks').then(r => r.ok ? r.json() : fallbackSpecs).then(data => { setSpecs(data); appendLog('success', `${data.length} blocks loaded into the library.`) }).catch(() => appendLog('warning', 'Backend unavailable; using the built-in block library.'))
  }, [appendLog])
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Delete' || !selectedId) return
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
      setNodes(items => items.filter(node => node.id !== selectedId))
      setEdges(items => items.filter(edge => edge.source !== selectedId && edge.target !== selectedId))
      setSelectedId(null)
      setRightTab('run')
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedId, setEdges, setNodes])
  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return
    const timer = window.setInterval(async () => {
      try { setJob(await getJob(job.id)) } catch (e) { const message = (e as Error).message; setError(message); appendLog('error', message) }
    }, 500)
    return () => window.clearInterval(timer)
  }, [appendLog, job?.id, job?.status])
  useEffect(() => {
    if (job?.status === 'completed' && job.result) appendLog('success', `Simulation completed · BER ${job.result.ber === null ? 'n/a' : job.result.ber.toExponential(3)} · ${job.result.snr_points.length} SNR points.`)
    if (job?.status === 'failed' && job.error) appendLog('error', job.error)
    if (job?.status === 'cancelled') appendLog('warning', 'Simulation cancelled by the user.')
  }, [appendLog, job?.status])
  useEffect(() => {
    if (job?.status !== 'running' || typeof job.snr_db !== 'number') return
    if (lastSnrRef.current === job.snr_db) return
    lastSnrRef.current = job.snr_db
    appendLog('info', `SNR ${job.snr_db.toFixed(2)} dB · point ${(job.snr_index ?? 0) + 1}/${job.snr_count ?? '?'}`)
  }, [appendLog, job?.snr_count, job?.snr_db, job?.snr_index, job?.status])

  const onConnect = useCallback((connection: Connection) => setEdges(eds => addEdge({ ...connection, markerEnd: { type: MarkerType.ArrowClosed }, animated: true }, eds)), [setEdges])
  const onNodeClick: NodeMouseHandler<FlowNode> = (_, node) => { setSelectedId(node.id); setRightTab('block') }
  const onNodeDragStart: OnNodeDrag<FlowNode> = (_, node) => { setSelectedId(node.id); setRightTab('block') }
  const updateSelected = (patch: Partial<FlowNode['data']>) => setNodes(items => items.map(n => n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n))
  const loadSourceFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selected) return
    const bytes = new Uint8Array(await file.arrayBuffer())
    let binary = ''
    for (let index = 0; index < bytes.length; index += 0x8000) binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
    updateSelected({ params: { ...selected.data.params, file_name: file.name, data_base64: btoa(binary) } })
    appendLog('success', `${file.name} loaded into ${selected.data.label} (${bytes.length.toLocaleString()} bytes).`)
  }
  const startResize = (side: 'left' | 'right', event: React.PointerEvent) => {
    event.preventDefault()
    resizeRef.current = { side, startX: event.clientX, startWidth: side === 'left' ? leftWidth : rightWidth }
    const move = (moveEvent: PointerEvent) => {
      const current = resizeRef.current
      if (!current) return
      const delta = moveEvent.clientX - current.startX
      if (current.side === 'left') setLeftWidth(Math.min(420, Math.max(210, current.startWidth + delta)))
      else setRightWidth(Math.min(520, Math.max(300, current.startWidth - delta)))
    }
    const stop = () => { resizeRef.current = null; window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop) }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', stop)
  }
  const startConsoleResize = (event: React.PointerEvent) => {
    event.preventDefault()
    consoleResizeRef.current = { startY: event.clientY, startHeight: consoleHeight }
    const move = (moveEvent: PointerEvent) => {
      const current = consoleResizeRef.current
      if (!current) return
      setConsoleHeight(Math.min(320, Math.max(92, current.startHeight - (moveEvent.clientY - current.startY))))
    }
    const stop = () => { consoleResizeRef.current = null; window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop) }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', stop)
  }

  const addBlock = (spec: BlockSpec) => {
    const id = `${spec.type}-${Date.now()}`
    const node: FlowNode = {
      id, type: 'signal', position: { x: 300 + Math.random() * 300, y: 140 + Math.random() * 300 },
      data: { label: spec.label, blockType: spec.type, category: spec.category, params: { ...spec.defaults }, inputs: spec.inputs, outputs: spec.outputs, portOrientation: 'standard', code: spec.type === 'python' ? pythonTemplate : undefined },
    }
    setNodes(ns => [...ns, node]); setSelectedId(id); setRightTab('block')
  }

  const run = async () => {
    setError(''); setRightTab('run'); lastSnrRef.current = null
    appendLog('info', `Starting Monte-Carlo sweep ${config.snr_db_start}…${config.snr_db_stop} dB.`)
    try {
      const id = await createJob(nodes, edges, config)
      const totalTrials = snrPointCount(config) * config.max_frames
      setJob({ id, status: 'queued', progress: 0, completed_trials: 0, trials: totalTrials })
      appendLog('info', `Job ${id.slice(0, 8)} queued · ${config.max_frames} max frames × ${snrPointCount(config)} SNR points.`)
    } catch (e) { const message = (e as Error).message; setError(message); appendLog('error', message) }
  }

  const exportProject = () => {
    const blob = new Blob([JSON.stringify({ graph: graphPayload(nodes, edges), config }, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'signallab-project.json'; a.click(); URL.revokeObjectURL(a.href)
  }
  const importProject = async (file?: File) => {
    if (!file) return
    try {
      const project = JSON.parse(await file.text())
      const specMap = new Map(specs.map(s => [s.type, s]))
      setNodes(project.graph.nodes.map((n: any) => ({
        id: n.id, type: 'signal', position: n.position,
        data: { label: n.label, blockType: n.type, category: specMap.get(n.type)?.category || '', params: n.params || {}, code: n.code, portOrientation: n.port_orientation || 'standard', inputs: specMap.get(n.type)?.inputs || ['in'], outputs: specMap.get(n.type)?.outputs || ['out'] },
      })))
      setEdges(project.graph.edges.map((e: any) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.source_handle, targetHandle: e.target_handle })))
      if (project.config) {
        const imported = project.config
        const importedMaxFrames = imported.max_frames ?? imported.trials ?? defaultSimulationConfig.max_frames
        setConfig({ ...defaultSimulationConfig, ...imported, trials: imported.trials ?? importedMaxFrames, max_frames: importedMaxFrames })
      }
      setSelectedId(null); setError('')
    } catch { setError('This project file is not valid JSON.') }
  }
  const grouped = useMemo(() => specs.filter(s => `${s.label} ${s.category}`.toLowerCase().includes(search.toLowerCase())).reduce<Record<string, BlockSpec[]>>((acc, spec) => ((acc[spec.category] ||= []).push(spec), acc), {}), [specs, search])
  const result = job?.result
  const livePoints = job?.status === 'running' ? (job.snr_points || []) : (result?.snr_points || job?.snr_points || [])

  return (
    <div className="app-shell" style={{ gridTemplateRows: `60px minmax(0, 1fr) ${consoleOpen ? consoleHeight : 0}px`, gridTemplateColumns: `${leftOpen ? leftWidth : 0}px minmax(0, 1fr) ${rightOpen ? rightWidth : 0}px` }}>
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><img src="/app-icon.svg" alt="SignalLab logo" /></div><div><strong>SignalLab</strong><span>Communications Studio</span></div></div>
        <div className="project-name"><span className="status-dot" /> <span>Hamming BPSK over AWGN</span></div>
        <div className="top-actions">
          <button className="ghost" onClick={() => setLeftOpen(value => !value)} title={leftOpen ? 'Hide block library' : 'Show block library'}><PanelLeft size={16} /></button>
          <button className="ghost" onClick={() => setRightOpen(value => !value)} title={rightOpen ? 'Hide inspector' : 'Show inspector'}><PanelRight size={16} /></button>
          <button className={`ghost ${consoleOpen ? 'active' : ''}`} onClick={() => setConsoleOpen(value => !value)} title={consoleOpen ? 'Hide console' : 'Show console'}><PanelBottom size={16} /></button>
          <button className="ghost" onClick={() => { setNodes(initialNodes); setEdges(initialEdges); setSelectedId('channel') }} title="Reset sample"><RotateCcw size={16} /></button>
          <button className="ghost labeled" onClick={() => fileRef.current?.click()}><Upload size={15} /> Import</button>
          <input ref={fileRef} type="file" accept=".json" hidden onChange={e => importProject(e.target.files?.[0])} />
          <button className="ghost labeled" onClick={exportProject}><Download size={15} /> Export</button>
        </div>
      </header>

      <aside className={`library ${leftOpen ? '' : 'collapsed'}`}>
        <div className="panel-title"><Layers3 size={16} /><span>Block library</span><small>{specs.length} blocks</small></div>
        <div className="search"><Search size={15} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search blocks…" /></div>
        <div className="library-list">
          {Object.entries(grouped).map(([category, blocks]) => <section key={category}><h4>{category}</h4>{blocks.map(spec => { const Icon = iconFor(spec.type); return <button className="block-item" key={spec.type} onClick={() => addBlock(spec)}><span className="block-icon"><Icon size={16} /></span><span><b>{spec.label}</b><small>{spec.description}</small></span><Plus size={14} /></button> })}</section>)}
        </div>
        {leftOpen && <div className="sidebar-resizer left-resizer" onPointerDown={event => startResize('left', event)} title="Resize block library" />}
      </aside>

      <main className="canvas-wrap">
        <div className="canvas-label"><span>FLOWGRAPH</span><span>{nodes.length} blocks · {edges.length} links</span></div>
        <ReactFlow nodes={nodes} edges={edges.map(e => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed }, animated: job?.status === 'running' }))} nodeTypes={{ signal: SignalNode }} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={onNodeClick} onNodeDragStart={onNodeDragStart} onPaneClick={() => setSelectedId(null)} fitView minZoom={0.2} maxZoom={2} defaultEdgeOptions={{ style: { strokeWidth: 2, stroke: '#7d8998' } }}>
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#ccd3dc" />
          <Controls position="bottom-left" />
          <MiniMap position="bottom-right" pannable zoomable offsetScale={4} nodeColor={node => miniMapColor(String((node.data as Record<string, unknown>)?.blockType || ''))} nodeStrokeColor="#ffffff" nodeStrokeWidth={1} nodeBorderRadius={3} nodeComponent={FlowMiniMapNode} bgColor="#f9fbfd" maskColor="rgba(226,233,242,.62)" maskStrokeColor="#8ea8ca" maskStrokeWidth={1} style={{ width: 150, height: 92, border: '1px solid #cbd6e3', borderRadius: 8, boxShadow: '0 3px 12px rgba(36,55,78,.14)' }} />
        </ReactFlow>
      </main>

      <aside className={`inspector ${rightOpen ? '' : 'collapsed'}`}>
        <div className="tabs"><button className={rightTab === 'run' ? 'active' : ''} onClick={() => setRightTab('run')}>Experiment</button><button className={rightTab === 'block' ? 'active' : ''} onClick={() => setRightTab('block')}>Block</button></div>
        {rightTab === 'block' ? selected ? <div className="inspector-content">
          <div className="selection-heading"><span className="large-icon">{selected.data.blockType === 'python' ? <Braces /> : <Box />}</span><div><small>SELECTED BLOCK</small><h3>{selected.data.label}</h3></div><button className="icon-danger" onClick={() => { setNodes(ns => ns.filter(n => n.id !== selected.id)); setEdges(es => es.filter(e => e.source !== selected.id && e.target !== selected.id)); setSelectedId(null) }}><X size={16} /></button></div>
          <label>Display name<input value={selected.data.label} onChange={e => updateSelected({ label: e.target.value })} /></label>
           <div className="port-layout-control"><div><span>Port layout</span><small>{selected.data.portOrientation === 'reversed' ? 'Input right · Output left' : 'Input left · Output right'}</small></div><button className={`port-toggle ${selected.data.portOrientation === 'reversed' ? 'active' : ''}`} onClick={() => updateSelected({ portOrientation: selected.data.portOrientation === 'reversed' ? 'standard' : 'reversed' })}><ArrowLeftRight size={15} /> {selected.data.portOrientation === 'reversed' ? 'Reversed' : 'Standard'}</button></div>
           <div className="section-rule"><span>PARAMETERS</span></div>
           {(selected.data.blockType === 'text_file_source' || selected.data.blockType === 'image_file_source') && <label>Input file<input type="file" accept={selected.data.blockType === 'image_file_source' ? 'image/*' : '.txt,.csv,.log,text/plain'} onChange={loadSourceFile} /><small>{String(selected.data.params.file_name || 'No file selected')}</small></label>}
           {selected.data.blockType === 'awgn' && <label>SNR source<select value={String(selected.data.params.snr_mode || 'experiment')} onChange={e => updateSelected({ params: { ...selected.data.params, snr_mode: e.target.value } })}><option value="experiment">Experiment sweep</option><option value="fixed">Fixed block value</option></select></label>}
           {selected.data.blockType === 'awgn' && String(selected.data.params.snr_mode || 'experiment') === 'fixed' && <label>Fixed SNR dB<input type="number" value={String(selected.data.params.ebn0_db ?? 4)} onChange={e => updateSelected({ params: { ...selected.data.params, ebn0_db: Number(e.target.value) } })} /></label>}
           {selected.data.blockType === 'image_file_source' && <label>Pixel mode<select value={String(selected.data.params.mode || 'grayscale')} onChange={e => updateSelected({ params: { ...selected.data.params, mode: e.target.value } })}><option value="grayscale">Grayscale</option><option value="rgb">RGB</option></select></label>}
           {visibleParams.length ? visibleParams.map(([key, value]) => <label key={key}>{key.replaceAll('_', ' ')}<input type={typeof value === 'number' ? 'number' : 'text'} value={String(value)} onChange={e => updateSelected({ params: { ...selected.data.params, [key]: typeof value === 'number' ? Number(e.target.value) : e.target.value } })} /></label>) : !['awgn', 'text_file_source', 'image_file_source'].includes(selected.data.blockType) && <p className="muted">This block has no parameters.</p>}
          {selected.data.blockType === 'ber' && livePoints.length ? <><div className="section-rule"><span>SINK PREVIEW</span></div><BerChart points={livePoints} live={job?.status === 'running'} /></> : null}
          {result?.sink_metrics && selected.data.blockType === 'power_meter' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean power</span><strong>{result.sink_metrics.power_mean?.toExponential(3) ?? '—'}</strong></div></div></>}
          {result?.sink_metrics && selected.data.blockType === 'scope' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean amplitude</span><strong>{result.sink_metrics.scope_mean_amplitude?.toFixed(4) ?? '—'}</strong></div><div><span>Peak</span><strong>{result.sink_metrics.scope_peak_amplitude?.toFixed(4) ?? '—'}</strong></div></div></>}
          {result?.sink_metrics && selected.data.blockType === 'constellation' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean I / Q</span><strong>{`${result.sink_metrics.constellation_mean_i?.toFixed(3) ?? '—'} / ${result.sink_metrics.constellation_mean_q?.toFixed(3) ?? '—'}`}</strong></div><div><span>Mean |x|</span><strong>{result.sink_metrics.constellation_mean_power?.toFixed(4) ?? '—'}</strong></div></div></>}
          {selected.data.blockType === 'python' && <><div className="section-rule"><span>PYTHON PROCESSOR</span><em>trusted local code</em></div><textarea className="code-editor" spellCheck={false} value={selected.data.code || pythonTemplate} onChange={e => updateSelected({ code: e.target.value })} /><p className="code-hint">Write <code>process(signal, params)</code> and return a NumPy array. SignalLab automatically runs independent Monte-Carlo trials in parallel.</p></>}
        </div> : <div className="empty-state"><Box size={32} /><h3>No block selected</h3><p>Select a block on the canvas to edit its parameters and Python code.</p></div> :
        <div className="inspector-content">
          <div className="experiment-title"><div><small>MONTE-CARLO</small><h2>Experiment</h2></div></div>
          <div className="section-rule"><span>SNR SWEEP (dB)</span></div>
          <div className="form-grid"><label>Start<input type="number" step="any" value={config.snr_db_start} onChange={e => setConfig({ ...config, snr_db_start: Number(e.target.value) })} /></label><label>Stop<input type="number" step="any" value={config.snr_db_stop} onChange={e => setConfig({ ...config, snr_db_stop: Number(e.target.value) })} /></label></div>
          <div className="form-grid"><label>Step<input type="number" min="0.01" step="any" value={config.snr_db_step} onChange={e => setConfig({ ...config, snr_db_step: Number(e.target.value) })} /></label><label>Max frames / SNR<input type="number" min="1" value={config.max_frames} onChange={e => { const value = Number(e.target.value); setConfig({ ...config, max_frames: value, trials: value }) }} /></label></div>
          <div className="form-grid"><label>Min frames / SNR<input type="number" min="1" value={config.min_frames} onChange={e => setConfig({ ...config, min_frames: Number(e.target.value) })} /></label><label>Min errors / SNR<input type="number" min="0" value={config.min_errors} onChange={e => setConfig({ ...config, min_errors: Number(e.target.value) })} /></label></div>
          <div className="section-rule"><span>RUNTIME</span></div>
          <div className="form-grid"><label>Workers<input type="number" min="0" value={config.workers} onChange={e => setConfig({ ...config, workers: Number(e.target.value) })} /><small>0 = auto</small></label><label>Seed<input type="number" value={config.seed} onChange={e => setConfig({ ...config, seed: Number(e.target.value) })} /></label></div>
          <label>Chunk size<input type="number" min="1" value={config.chunk_size} onChange={e => setConfig({ ...config, chunk_size: Number(e.target.value) })} /></label>
          <label>Compute device<select value={config.device} onChange={e => setConfig({ ...config, device: e.target.value as SimulationConfig['device'] })}><option value="auto">Auto · best available</option><option value="cpu">CPU · multiprocessing</option><option value="gpu">GPU · CUDA/CuPy</option></select></label>
          <button className="run-wide" onClick={run} disabled={job?.status === 'running'}><Play size={16} fill="currentColor" /> {job?.status === 'running' ? 'Simulation running…' : 'Run simulation'}</button>
          {job && <div className="job-card"><div className="job-line"><span><i className={`job-dot ${job.status}`} />{job.status}</span><b>{Math.round((job.progress || 0) * 100)}%</b></div><div className="progress"><span style={{ width: `${(job.progress || 0) * 100}%` }} /></div><div className="job-meta"><span>{job.completed_trials || 0} / {job.trials} trials</span><span>{job.device || result?.device || 'preparing'}</span></div>{job.status === 'running' && <button className="cancel" onClick={() => cancelJob(job.id)}><CircleStop size={14} /> Cancel</button>}</div>}
          {error && <div className="error-box">{error}</div>}
          {(result || livePoints.length > 0) && <div className="results">
            <div className="section-rule"><span>{job?.status === 'running' ? 'LIVE RESULTS' : 'RESULTS'}</span></div>
            {result && <div className="overall-ber-card"><div><span>OVERALL BIT ERROR RATE</span><small>Aggregate across the complete experiment</small></div><strong>{result.ber === null ? '—' : result.ber.toExponential(3)}</strong></div>}
            <div className="ber-plot-section"><div className="section-rule"><span>BER VS SNR</span></div><BerChart points={livePoints} live={job?.status === 'running'} /></div>
            <ResultsTable points={livePoints} />
            {result && <><div className="metric-row"><div className="metric"><span>Bit errors</span><strong>{formatNumber(result.bit_errors)}</strong></div><div className="metric"><span>Total bits</span><strong>{formatNumber(result.total_bits)}</strong></div></div><div className="metric-row"><div className="metric"><span>Elapsed</span><strong>{result.elapsed_seconds.toFixed(2)} s</strong></div><div className="metric"><span>Throughput</span><strong>{formatNumber(result.throughput_bps / 1000)} kb/s</strong></div></div>{result.warnings?.map(w => <p className="warning" key={w}>{w}</p>)}</>}
          </div>}
        </div>}
        {rightOpen && <div className="sidebar-resizer right-resizer" onPointerDown={event => startResize('right', event)} title="Resize inspector" />}
      </aside>

      {consoleOpen && <section className="console-dock">
        <div className="console-resizer" onPointerDown={startConsoleResize} title="Resize console" />
        <div className="console-header"><div><Terminal size={15} /><strong>Console</strong><span>{consoleEntries.length} events</span></div><button className="console-clear" onClick={() => setConsoleEntries([])} title="Clear console"><Trash2 size={14} /></button></div>
        <div className="console-body">
          {consoleEntries.length ? consoleEntries.map(entry => <div className={`console-line ${entry.level}`} key={entry.id}><time>{entry.time}</time><b>{entry.level}</b><span>{entry.message}</span></div>) : <div className="console-empty">No messages yet.</div>}
        </div>
      </section>}
    </div>
  )
}

export default App
