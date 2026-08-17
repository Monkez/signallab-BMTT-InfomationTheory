import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState,
  BackgroundVariant, MarkerType, type Connection, type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Activity, Box, Braces, ChevronDown, CircleStop, Cpu, Download, Gauge,
  Layers3, Play, Plus, Radio, RotateCcw, Search, Upload, Waves, X, Zap,
} from 'lucide-react'
import { SignalNode } from './SignalNode'
import { cancelJob, createJob, getJob, graphPayload } from './api'
import { initialEdges, initialNodes, pythonTemplate } from './sample'
import type { BlockSpec, FlowNode, Job, SimulationConfig } from './types'

const fallbackSpecs: BlockSpec[] = [
  { type: 'bit_source', label: 'Bit Source', category: 'Sources', description: 'Random binary messages', defaults: { length: 4096 }, inputs: [], outputs: ['out'], gpu_compatible: true },
  { type: 'hamming74_encode', label: 'Hamming Encoder', category: 'Channel coding', description: 'Hamming (7,4)', defaults: {}, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: true },
  { type: 'bpsk_mod', label: 'BPSK Modulator', category: 'Modulation', description: 'Binary phase shift keying', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'awgn', label: 'AWGN Channel', category: 'Channels', description: 'Add white Gaussian noise', defaults: { ebn0_db: 4 }, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'bpsk_demod', label: 'BPSK Demodulator', category: 'Receivers', description: 'Hard decision', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'hamming74_decode', label: 'Hamming Decoder', category: 'Channel coding', description: 'Correct one bit', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'ber', label: 'BER Meter', category: 'Sinks', description: 'Measure bit error rate', defaults: {}, inputs: ['reference', 'estimate'], outputs: [], gpu_compatible: true },
  { type: 'python', label: 'Python Block', category: 'Custom', description: 'Custom NumPy processing', defaults: { gain: 1 }, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
]

const iconFor = (type: string) => type.includes('awgn') ? Waves : type.includes('bpsk') ? Radio : type === 'ber' ? Gauge : type === 'python' ? Braces : Box
const formatNumber = (n: number) => new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(n)

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [specs, setSpecs] = useState<BlockSpec[]>(fallbackSpecs)
  const [selectedId, setSelectedId] = useState<string | null>('channel')
  const [search, setSearch] = useState('')
  const [config, setConfig] = useState<SimulationConfig>({ trials: 100, workers: 0, seed: 2026, device: 'auto', chunk_size: 10 })
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [rightTab, setRightTab] = useState<'block' | 'run'>('run')
  const fileRef = useRef<HTMLInputElement>(null)
  const selected = nodes.find(n => n.id === selectedId)

  useEffect(() => { fetch('/api/blocks').then(r => r.ok ? r.json() : fallbackSpecs).then(setSpecs).catch(() => {}) }, [])
  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return
    const timer = window.setInterval(async () => {
      try { setJob(await getJob(job.id)) } catch (e) { setError((e as Error).message) }
    }, 500)
    return () => window.clearInterval(timer)
  }, [job?.id, job?.status])

  const onConnect = useCallback((connection: Connection) => setEdges(eds => addEdge({ ...connection, markerEnd: { type: MarkerType.ArrowClosed }, animated: true }, eds)), [setEdges])
  const onNodeClick: NodeMouseHandler<FlowNode> = (_, node) => { setSelectedId(node.id); setRightTab('block') }
  const updateSelected = (patch: Partial<FlowNode['data']>) => setNodes(items => items.map(n => n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n))

  const addBlock = (spec: BlockSpec) => {
    const id = `${spec.type}-${Date.now()}`
    const node: FlowNode = {
      id, type: 'signal', position: { x: 300 + Math.random() * 300, y: 140 + Math.random() * 300 },
      data: { label: spec.label, blockType: spec.type, category: spec.category, params: { ...spec.defaults }, inputs: spec.inputs, outputs: spec.outputs, code: spec.type === 'python' ? pythonTemplate : undefined },
    }
    setNodes(ns => [...ns, node]); setSelectedId(id); setRightTab('block')
  }

  const run = async () => {
    setError(''); setRightTab('run')
    try {
      const id = await createJob(nodes, edges, config)
      setJob({ id, status: 'queued', progress: 0, completed_trials: 0, trials: config.trials })
    } catch (e) { setError((e as Error).message) }
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
        data: { label: n.label, blockType: n.type, category: specMap.get(n.type)?.category || '', params: n.params || {}, code: n.code, inputs: specMap.get(n.type)?.inputs || ['in'], outputs: specMap.get(n.type)?.outputs || ['out'] },
      })))
      setEdges(project.graph.edges.map((e: any) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.source_handle, targetHandle: e.target_handle })))
      if (project.config) setConfig(project.config)
      setSelectedId(null); setError('')
    } catch { setError('This project file is not valid JSON.') }
  }
  const grouped = useMemo(() => specs.filter(s => `${s.label} ${s.category}`.toLowerCase().includes(search.toLowerCase())).reduce<Record<string, BlockSpec[]>>((acc, spec) => ((acc[spec.category] ||= []).push(spec), acc), {}), [specs, search])
  const result = job?.result

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Activity size={18} /></div><div><strong>SignalLab</strong><span>Communications Studio</span></div></div>
        <div className="project-name"><span className="status-dot" /> Hamming BPSK over AWGN <ChevronDown size={14} /></div>
        <div className="top-actions">
          <button className="ghost" onClick={() => { setNodes(initialNodes); setEdges(initialEdges); setSelectedId('channel') }} title="Reset sample"><RotateCcw size={16} /></button>
          <button className="ghost labeled" onClick={() => fileRef.current?.click()}><Upload size={15} /> Import</button>
          <input ref={fileRef} type="file" accept=".json" hidden onChange={e => importProject(e.target.files?.[0])} />
          <button className="ghost labeled" onClick={exportProject}><Download size={15} /> Export</button>
          <button className="run-button" onClick={run} disabled={job?.status === 'running'}><Play size={15} fill="currentColor" /> Run simulation</button>
        </div>
      </header>

      <aside className="library">
        <div className="panel-title"><Layers3 size={16} /><span>Block library</span></div>
        <div className="search"><Search size={15} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search blocks…" /></div>
        <div className="library-list">
          {Object.entries(grouped).map(([category, blocks]) => <section key={category}><h4>{category}</h4>{blocks.map(spec => { const Icon = iconFor(spec.type); return <button className="block-item" key={spec.type} onClick={() => addBlock(spec)}><span className="block-icon"><Icon size={16} /></span><span><b>{spec.label}</b><small>{spec.description}</small></span><Plus size={14} /></button> })}</section>)}
        </div>
        <div className="compute-card"><Zap size={16} /><div><b>Parallel runtime</b><small>Auto-scales across CPU cores and CUDA</small></div></div>
      </aside>

      <main className="canvas-wrap">
        <div className="canvas-label"><span>FLOWGRAPH</span><span>{nodes.length} blocks · {edges.length} links</span></div>
        <ReactFlow nodes={nodes} edges={edges.map(e => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed }, animated: job?.status === 'running' }))} nodeTypes={{ signal: SignalNode }} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={onNodeClick} onPaneClick={() => setSelectedId(null)} fitView minZoom={0.2} maxZoom={2} defaultEdgeOptions={{ style: { strokeWidth: 2, stroke: '#7d8998' } }}>
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#ccd3dc" />
          <Controls position="bottom-left" />
          <MiniMap position="bottom-right" pannable zoomable nodeColor="#7c8da5" maskColor="rgba(235,239,244,.72)" />
        </ReactFlow>
      </main>

      <aside className="inspector">
        <div className="tabs"><button className={rightTab === 'run' ? 'active' : ''} onClick={() => setRightTab('run')}>Experiment</button><button className={rightTab === 'block' ? 'active' : ''} onClick={() => setRightTab('block')}>Block</button></div>
        {rightTab === 'block' ? selected ? <div className="inspector-content">
          <div className="selection-heading"><span className="large-icon">{selected.data.blockType === 'python' ? <Braces /> : <Box />}</span><div><small>SELECTED BLOCK</small><h3>{selected.data.label}</h3></div><button className="icon-danger" onClick={() => { setNodes(ns => ns.filter(n => n.id !== selected.id)); setEdges(es => es.filter(e => e.source !== selected.id && e.target !== selected.id)); setSelectedId(null) }}><X size={16} /></button></div>
          <label>Display name<input value={selected.data.label} onChange={e => updateSelected({ label: e.target.value })} /></label>
          <div className="section-rule"><span>PARAMETERS</span></div>
          {Object.entries(selected.data.params).length ? Object.entries(selected.data.params).map(([key, value]) => <label key={key}>{key.replaceAll('_', ' ')}<input type={typeof value === 'number' ? 'number' : 'text'} value={String(value)} onChange={e => updateSelected({ params: { ...selected.data.params, [key]: typeof value === 'number' ? Number(e.target.value) : e.target.value } })} /></label>) : <p className="muted">This block has no parameters.</p>}
          {selected.data.blockType === 'python' && <><div className="section-rule"><span>PYTHON PROCESSOR</span><em>trusted local code</em></div><textarea className="code-editor" spellCheck={false} value={selected.data.code || pythonTemplate} onChange={e => updateSelected({ code: e.target.value })} /><p className="code-hint">Use <code>context.xp</code> for CPU/GPU portable array operations.</p></>}
        </div> : <div className="empty-state"><Box size={32} /><h3>No block selected</h3><p>Select a block on the canvas to edit its parameters and Python code.</p></div> :
        <div className="inspector-content">
          <div className="experiment-title"><div><small>MONTE-CARLO</small><h2>Experiment</h2></div><span className="engine-pill"><Cpu size={13} /> local engine</span></div>
          <div className="form-grid"><label>Trials<input type="number" min="1" value={config.trials} onChange={e => setConfig({ ...config, trials: Number(e.target.value) })} /></label><label>Workers<input type="number" min="0" value={config.workers} onChange={e => setConfig({ ...config, workers: Number(e.target.value) })} /><small>0 = auto</small></label></div>
          <div className="form-grid"><label>Seed<input type="number" value={config.seed} onChange={e => setConfig({ ...config, seed: Number(e.target.value) })} /></label><label>Chunk size<input type="number" min="1" value={config.chunk_size} onChange={e => setConfig({ ...config, chunk_size: Number(e.target.value) })} /></label></div>
          <label>Compute device<select value={config.device} onChange={e => setConfig({ ...config, device: e.target.value as SimulationConfig['device'] })}><option value="auto">Auto · best available</option><option value="cpu">CPU · multiprocessing</option><option value="gpu">GPU · CUDA/CuPy</option></select></label>
          <button className="run-wide" onClick={run} disabled={job?.status === 'running'}><Play size={16} fill="currentColor" /> {job?.status === 'running' ? 'Simulation running…' : 'Run simulation'}</button>
          {job && <div className="job-card"><div className="job-line"><span><i className={`job-dot ${job.status}`} />{job.status}</span><b>{Math.round((job.progress || 0) * 100)}%</b></div><div className="progress"><span style={{ width: `${(job.progress || 0) * 100}%` }} /></div><div className="job-meta"><span>{job.completed_trials || 0} / {job.trials} trials</span><span>{job.device || result?.device || 'preparing'}</span></div>{job.status === 'running' && <button className="cancel" onClick={() => cancelJob(job.id)}><CircleStop size={14} /> Cancel</button>}</div>}
          {error && <div className="error-box">{error}</div>}
          {result && <div className="results"><div className="section-rule"><span>RESULTS</span></div><div className="metric hero"><span>Bit error rate</span><strong>{result.ber === null ? '—' : result.ber.toExponential(3)}</strong></div><div className="metric-row"><div className="metric"><span>Bit errors</span><strong>{formatNumber(result.bit_errors)}</strong></div><div className="metric"><span>Total bits</span><strong>{formatNumber(result.total_bits)}</strong></div></div><div className="metric-row"><div className="metric"><span>Elapsed</span><strong>{result.elapsed_seconds.toFixed(2)} s</strong></div><div className="metric"><span>Throughput</span><strong>{formatNumber(result.throughput_bps / 1000)} kb/s</strong></div></div>{result.warnings?.map(w => <p className="warning" key={w}>{w}</p>)}</div>}
        </div>}
      </aside>
    </div>
  )
}

export default App
