import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState,
  BackgroundVariant, MarkerType, type Connection, type EdgeChange, type NodeMouseHandler, type OnNodeDrag,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Activity, ArrowLeftRight, BookOpen, Box, Braces, CircleStop, FilePlus2, FolderOpen,
  Copy, Layers3, LibraryBig, Maximize2, PanelBottom, PanelLeft, PanelRight, Play, Plus, RotateCcw, Save, SaveAll, Search, Terminal, Trash2, X,
} from 'lucide-react'
import { SignalNode } from './SignalNode'
import { cancelJob, createJob, getJob, graphPayload, GraphApiError, runGraphOnce } from './api'
import { initialEdges, initialNodes, pythonTemplate } from './sample'
import type { BlockSpec, FlowEdge, FlowNode, Job, PortPreviewMap, SimulationConfig } from './types'
import { BerChart } from './SinkChart'
import { ResultsTable } from './ResultsTable'
import { SinkResults } from './SinkResults'
import { FlowMiniMapNode } from './components/FlowMiniMapNode'
import { fallbackSpecs, iconFor, miniMapColor } from './features/blocks/catalog'
import { PortDataInspector } from './features/blocks/PortDataInspector'
import { defaultSimulationConfig, snrPointCount, validateSimulationConfig } from './features/experiment/config'
import { HuffmanCodebookTable } from './features/sourceTheory/HuffmanCodebookTable'
import { SampleLibraryModal } from './features/samples/SampleLibraryModal'
import { materializeSample, type SampleProject } from './features/samples/types'
import { VariablesEditor } from './features/variables/VariablesEditor'
import { parsePythonPorts } from './features/pythonEditor/ports'
import {
  attachBrowserProjectFile, clearProjectFileTarget, openProjectFile, projectDisplayName,
  saveProjectFile, supportsProjectOpenDialog,
} from './features/projects/projectFiles'

const formatNumber = (n: number) => new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(n)
const parameterLabel = (key: string) => key === 'include_header' ? 'Include 32-bit symbol-count header' : key.replaceAll('_', ' ')
type ConsoleLevel = 'info' | 'success' | 'warning' | 'error'
type ConsoleEntry = { id: number; time: string; level: ConsoleLevel; message: string }

const projectSignature = (nodes: FlowNode[], edges: FlowEdge[], config: SimulationConfig) =>
  JSON.stringify({ graph: graphPayload(nodes, edges), config })

const openDocuments = () => {
  const url = new URL(window.location.href)
  url.hash = '/documents'
  window.open(url.toString(), 'signallab-documents', 'popup=yes,width=1240,height=820,resizable=yes,scrollbars=yes')?.focus()
}

const PythonCodeEditor = lazy(() => import('./features/pythonEditor/PythonCodeEditor').then(module => ({ default: module.PythonCodeEditor })))
const PythonEditorModal = lazy(() => import('./features/pythonEditor/PythonEditorModal').then(module => ({ default: module.PythonEditorModal })))

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [specs, setSpecs] = useState<BlockSpec[]>(fallbackSpecs)
  const [selectedId, setSelectedId] = useState<string | null>('channel')
  const [search, setSearch] = useState('')
  const [config, setConfig] = useState<SimulationConfig>(defaultSimulationConfig)
  const [job, setJob] = useState<Job | null>(null)
  const [runOnceActive, setRunOnceActive] = useState(false)
  const [runOnceMetrics, setRunOnceMetrics] = useState<Record<string, number>>({})
  const [runOnceSinkMetrics, setRunOnceSinkMetrics] = useState<Record<string, number>>({})
  const [snapshotId, setSnapshotId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [rightTab, setRightTab] = useState<'block' | 'run'>('run')
  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)
  const [leftWidth, setLeftWidth] = useState(270)
  const [rightWidth, setRightWidth] = useState(360)
  const [consoleOpen, setConsoleOpen] = useState(true)
  const [consoleHeight, setConsoleHeight] = useState(156)
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([])
  const [consoleCopied, setConsoleCopied] = useState(false)
  const [projectName, setProjectName] = useState('Hamming BPSK over AWGN')
  const [savedSignature, setSavedSignature] = useState(() => projectSignature(initialNodes, initialEdges, defaultSimulationConfig))
  const [savingProject, setSavingProject] = useState(false)
  const [samplesOpen, setSamplesOpen] = useState(false)
  const [pythonEditorOpen, setPythonEditorOpen] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const bootLoggedRef = useRef(false)
  const lastSnrRef = useRef<number | null>(null)
  const consoleResizeRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const resizeRef = useRef<{ side: 'left' | 'right'; startX: number; startWidth: number } | null>(null)
  const selected = nodes.find(n => n.id === selectedId)
  const selectedSpec = selected ? specs.find(spec => spec.type === selected.data.blockType) : undefined
  const jobActive = job?.status === 'queued' || job?.status === 'running'
  const executionActive = jobActive || runOnceActive
  const currentSignature = useMemo(() => projectSignature(nodes, edges, config), [config, edges, nodes])
  const projectDirty = currentSignature !== savedSignature
  const configIssue = validateSimulationConfig(config)
  const selectedIsStochasticChannel = selected ? ['awgn', 'rayleigh'].includes(selected.data.blockType) : false
  const selectedIsFileSource = selected ? ['text_file_source', 'text_file_symbol_source', 'image_file_source'].includes(selected.data.blockType) : false
  const visibleParams = selected ? Object.entries(selected.data.params).filter(([key]) => {
    if (key === 'data_base64' || key === 'file_name') return false
    if (selected.data.blockType === 'variables' && key === 'definitions') return false
    if (selectedIsStochasticChannel && (key === 'snr_mode' || key === 'ebn0_db')) return false
    if (selected.data.blockType === 'image_file_source' && key === 'mode') return false
    return true
  }) : []
  const appendLog = useCallback((level: ConsoleLevel, message: string) => {
    setConsoleEntries(entries => [...entries.slice(-199), { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), level, message }])
  }, [])
  const copyConsole = useCallback(async () => {
    const text = consoleEntries.map(entry => `[${entry.time}] ${entry.level.toUpperCase()} ${entry.message}`).join('\n')
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setConsoleCopied(true)
      window.setTimeout(() => setConsoleCopied(false), 1400)
    } catch (cause) {
      appendLog('warning', `Could not copy console text: ${(cause as Error).message || 'clipboard unavailable'}`)
    }
  }, [appendLog, consoleEntries])
  const applyPortPreviews = useCallback((previews: PortPreviewMap) => {
    setNodes(items => items.map(node => ({ ...node, data: { ...node.data, portPreviews: previews[node.id] } })))
  }, [setNodes])
  const clearDiagnostics = useCallback(() => {
    setSnapshotId(null)
    setRunOnceMetrics({})
    setRunOnceSinkMetrics({})
    setNodes(items => items.map(node => node.data.portPreviews || node.data.runtimeError ? { ...node, data: { ...node.data, portPreviews: undefined, runtimeError: undefined } } : node))
  }, [setNodes])
  const applyNodeErrors = useCallback((errors: Record<string, string[]>) => {
    setNodes(items => items.map(node => ({ ...node, data: { ...node.data, runtimeError: errors[node.id]?.join(' · ') } })))
  }, [setNodes])
  const executionError = useCallback((cause: unknown) => {
    const issue = cause as Error
    if (cause instanceof GraphApiError) applyNodeErrors(cause.nodeErrors)
    const message = issue.message || 'Graph execution failed'
    setError(message)
    appendLog('error', message)
  }, [appendLog, applyNodeErrors])

  useEffect(() => { clearDiagnostics() }, [clearDiagnostics, config])

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
      setNodes(items => items.filter(node => node.id !== selectedId).map(node => ({ ...node, data: { ...node.data, portPreviews: undefined, runtimeError: undefined } })))
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
    if (job?.status === 'completed' && job.result) {
      applyPortPreviews(job.result.port_previews || {})
      setSnapshotId(job.result.snapshot_id || null)
      appendLog('success', `Benchmark completed · BER ${job.result.ber === null ? 'n/a' : job.result.ber.toExponential(3)} · ${job.result.snr_points.length} SNR points.`)
    }
    if (job?.status === 'failed' && job.error) {
      applyNodeErrors(job.node_errors || {})
      setError(job.error)
      appendLog('error', job.error)
    }
    if (job?.status === 'cancelled') appendLog('warning', 'Benchmark cancelled by the user.')
  }, [appendLog, applyNodeErrors, applyPortPreviews, job?.status])
  useEffect(() => {
    if (job?.status !== 'completed') return
    window.setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
  }, [job?.status])
  useEffect(() => {
    if (job?.status !== 'running' || typeof job.snr_db !== 'number') return
    if (lastSnrRef.current === job.snr_db) return
    lastSnrRef.current = job.snr_db
    appendLog('info', `SNR ${job.snr_db.toFixed(2)} dB · point ${(job.snr_index ?? 0) + 1}/${job.snr_count ?? '?'}`)
  }, [appendLog, job?.snr_count, job?.snr_db, job?.snr_index, job?.status])

  const onConnect = useCallback((connection: Connection) => { clearDiagnostics(); setEdges(eds => addEdge({ ...connection, markerEnd: { type: MarkerType.ArrowClosed }, animated: true }, eds)) }, [clearDiagnostics, setEdges])
  const onEdgesChangeWithPreview = useCallback((changes: EdgeChange[]) => {
    if (changes.some(change => change.type === 'remove')) clearDiagnostics()
    onEdgesChange(changes)
  }, [clearDiagnostics, onEdgesChange])
  const onNodeClick: NodeMouseHandler<FlowNode> = (_, node) => { setSelectedId(node.id); setRightTab('block') }
  const onNodeDragStart: OnNodeDrag<FlowNode> = (_, node) => { setSelectedId(node.id); setRightTab('block') }
  const updateSelected = (patch: Partial<FlowNode['data']>) => setNodes(items => items.map(n => ({ ...n, data: { ...n.data, ...(n.id === selectedId ? patch : {}), portPreviews: undefined, runtimeError: undefined } })))
  const updatePythonCode = (code: string) => {
    if (!selected || selected.data.blockType !== 'python') return
    const layout = parsePythonPorts(code)
    const nextInputs = new Set(layout.inputs)
    const nextOutputs = new Set(layout.outputs)
    const removed = edges.filter(edge => (edge.source === selected.id && !nextOutputs.has(edge.sourceHandle || 'out')) || (edge.target === selected.id && !nextInputs.has(edge.targetHandle || 'in')))
    if (removed.length) appendLog('warning', `${removed.length} connection${removed.length === 1 ? '' : 's'} removed because the Python port declaration changed.`)
    if (removed.length) setEdges(items => items.filter(edge => !removed.some(item => item.id === edge.id)))
    updateSelected({ code, inputs: layout.inputs, outputs: layout.outputs })
  }
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
    if (spec.type === 'variables' && nodes.some(node => node.data.blockType === 'variables')) {
      const existing = nodes.find(node => node.data.blockType === 'variables')!
      setSelectedId(existing.id); setRightTab('block')
      appendLog('warning', 'A simulation can contain only one Variables block; selected the existing block.')
      return
    }
    clearDiagnostics()
    const id = `${spec.type}-${Date.now()}`
    const node: FlowNode = {
      id, type: 'signal', position: { x: 300 + Math.random() * 300, y: 140 + Math.random() * 300 },
      data: { label: spec.label, blockType: spec.type, category: spec.category, params: { ...spec.defaults }, inputs: spec.inputs, outputs: spec.outputs, portOrientation: 'standard', code: spec.type === 'python' ? pythonTemplate : undefined },
    }
    setNodes(ns => [...ns, node]); setSelectedId(id); setRightTab('block')
  }

  const runOnce = async () => {
    if (configIssue) { setError(configIssue); return }
    clearDiagnostics()
    setError(''); setRightTab('run'); setRunOnceActive(true); setJob(null)
    appendLog('info', `Running one frame at ${config.snr_db_start} dB…`)
    try {
      const snapshot = await runGraphOnce(nodes, edges, config)
      applyPortPreviews(snapshot.port_previews)
      setSnapshotId(snapshot.snapshot_id)
      setRunOnceMetrics(snapshot.metrics)
      setRunOnceSinkMetrics(snapshot.sink_metrics || {})
      appendLog('success', `Run once completed in ${(snapshot.elapsed_seconds * 1000).toFixed(1)} ms on ${snapshot.device.toUpperCase()} · hover any port to inspect data.`)
    } catch (e) { executionError(e) } finally { setRunOnceActive(false) }
  }

  const runBenchmark = async () => {
    if (configIssue) { setError(configIssue); return }
    setError(''); setRightTab('run'); lastSnrRef.current = null; setRunOnceMetrics({}); setRunOnceSinkMetrics({})
    clearDiagnostics()
    appendLog('info', `Starting Monte-Carlo benchmark ${config.snr_db_start}…${config.snr_db_stop} dB.`)
    try {
      const id = await createJob(nodes, edges, config)
      const totalTrials = snrPointCount(config) * config.max_frames
      setJob({ id, status: 'queued', progress: 0, completed_trials: 0, trials: totalTrials })
      appendLog('info', `Job ${id.slice(0, 8)} queued · ${config.max_frames} max frames × ${snrPointCount(config)} SNR points.`)
    } catch (e) { executionError(e) }
  }

  const projectDocument = useCallback(() => JSON.stringify({
    format: 'signallab-simulation',
    version: '1.0',
    saved_at: new Date().toISOString(),
    graph: graphPayload(nodes, edges),
    config,
  }, null, 2), [config, edges, nodes])

  const applyProject = useCallback((content: string, filename: string) => {
    try {
      const project = JSON.parse(content)
      if (!project?.graph || !Array.isArray(project.graph.nodes) || !Array.isArray(project.graph.edges)) throw new Error('Missing graph data')
      const specMap = new Map(specs.map(s => [s.type, s]))
      const importedNodes = project.graph.nodes.map((n: any) => {
        const pythonPorts = n.type === 'python' ? parsePythonPorts(n.code || '') : undefined
        return {
        id: n.id, type: 'signal', position: n.position,
        data: { label: n.label, blockType: n.type, category: specMap.get(n.type)?.category || '', params: { ...(specMap.get(n.type)?.defaults || {}), ...(n.params || {}) }, code: n.code, portOrientation: n.port_orientation || 'standard', inputs: pythonPorts?.inputs || specMap.get(n.type)?.inputs || ['in'], outputs: pythonPorts?.outputs || specMap.get(n.type)?.outputs || ['out'] },
        }
      }) as FlowNode[]
      const importedEdges = project.graph.edges.map((e: any) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.source_handle, targetHandle: e.target_handle }))
      const imported = project.config || {}
      const importedMaxFrames = imported.max_frames ?? imported.trials ?? defaultSimulationConfig.max_frames
      const importedConfig = { ...defaultSimulationConfig, ...imported, trials: imported.trials ?? importedMaxFrames, max_frames: importedMaxFrames }
      setNodes(importedNodes)
      setEdges(importedEdges)
      setConfig(importedConfig)
      setSavedSignature(projectSignature(importedNodes, importedEdges, importedConfig))
      setProjectName(projectDisplayName(filename))
      setSelectedId(null); setJob(null); setSnapshotId(null); setError('')
      appendLog('success', `${filename} opened · ${importedNodes.length} blocks and ${importedEdges.length} links.`)
      return true
    } catch {
      setError('This SignalLab simulation file is not valid.')
      appendLog('error', `Could not open ${filename}: invalid simulation file.`)
      return false
    }
  }, [appendLog, setEdges, setNodes, specs])

  const saveProject = useCallback(async (saveAs = false) => {
    if (savingProject) return
    setSavingProject(true)
    try {
      const result = await saveProjectFile(projectDocument(), projectName, saveAs)
      if (!result) return
      const filename = result.name || `${projectName}.slab.json`
      setProjectName(projectDisplayName(filename))
      setSavedSignature(currentSignature)
      appendLog('success', `${filename} saved${result.direct === false ? ' as a download' : ''}.`)
    } catch (cause) {
      if ((cause as DOMException).name !== 'AbortError') {
        const message = (cause as Error).message || 'Could not save the simulation file.'
        setError(message); appendLog('error', message)
      }
    } finally { setSavingProject(false) }
  }, [appendLog, currentSignature, projectDocument, projectName, savingProject])

  const openProject = useCallback(async () => {
    if (projectDirty && !window.confirm('Discard unsaved changes and open another simulation?')) return
    try {
      if (!supportsProjectOpenDialog()) { fileRef.current?.click(); return }
      const opened = await openProjectFile()
      if (opened?.content && !applyProject(opened.content, opened.name || 'simulation.slab.json')) await clearProjectFileTarget()
    } catch (cause) {
      if ((cause as DOMException).name !== 'AbortError') {
        const message = (cause as Error).message || 'Could not open the simulation file.'
        setError(message); appendLog('error', message)
      }
    }
  }, [appendLog, applyProject, projectDirty])

  const importProject = async (file?: File) => {
    if (!file) return
    const opened = await attachBrowserProjectFile(file)
    applyProject(opened.content, opened.name)
  }

  const newSimulation = () => {
    if (projectDirty && !window.confirm('Discard unsaved changes and create a new simulation?')) return
    clearDiagnostics()
    setNodes([])
    setEdges([])
    setConfig({ ...defaultSimulationConfig })
    setSelectedId(null)
    setJob(null)
    setSnapshotId(null)
    setError('')
    setRightTab('run')
    setProjectName('Untitled simulation')
    setSavedSignature('')
    lastSnrRef.current = null
    void clearProjectFileTarget()
    appendLog('info', 'New blank simulation created. Use Save to choose a project file.')
  }

  const resetSample = () => {
    if (projectDirty && !window.confirm('Discard unsaved changes and reset the sample simulation?')) return
    clearDiagnostics(); setNodes(initialNodes); setEdges(initialEdges); setSelectedId('channel'); setJob(null)
    setProjectName('Hamming BPSK over AWGN'); setSavedSignature('')
    void clearProjectFileTarget()
    appendLog('info', 'Sample simulation restored. Save it to create a new project file.')
  }

  const openCatalogSample = (sample: SampleProject) => {
    if (projectDirty && !window.confirm('Discard unsaved changes and open this sample?')) return
    const materialized = materializeSample(sample, specs)
    clearDiagnostics()
    setNodes(materialized.nodes)
    setEdges(materialized.edges)
    setConfig(materialized.config)
    setSelectedId(null)
    setJob(null)
    setSnapshotId(null)
    setError('')
    setRightTab('run')
    setProjectName(sample.sample.title)
    setSavedSignature('')
    lastSnrRef.current = null
    void clearProjectFileTarget()
    setSamplesOpen(false)
    appendLog('success', `Sample “${sample.sample.title}” opened · ${materialized.nodes.length} blocks and ${materialized.edges.length} links.`)
    appendLog('info', `Learning goal: ${sample.sample.learning_objectives[0]}`)
  }

  useEffect(() => {
    const onSaveShortcut = (event: KeyboardEvent) => {
      if (event.defaultPrevented || !(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 's') return
      event.preventDefault()
      void saveProject(event.shiftKey)
    }
    window.addEventListener('keydown', onSaveShortcut)
    return () => window.removeEventListener('keydown', onSaveShortcut)
  }, [saveProject])
  const grouped = useMemo(() => specs.filter(s => `${s.label} ${s.category}`.toLowerCase().includes(search.toLowerCase())).reduce<Record<string, BlockSpec[]>>((acc, spec) => ((acc[spec.category] ||= []).push(spec), acc), {}), [specs, search])
  const result = job?.result
  const livePoints = job?.status === 'running' ? (job.snr_points || []) : (result?.snr_points || job?.snr_points || [])
  const activeSinkMetrics = result?.sink_metrics || runOnceSinkMetrics
  const hasBerSink = nodes.some(node => node.data.blockType === 'ber')
  const sinkNodes = nodes.filter(node => ['ber', 'power_meter', 'constellation', 'scope', 'source_analyzer', 'ser'].includes(node.data.blockType))
  const hasSinkResults = sinkNodes.some(node => node.data.blockType !== 'ber') && Object.keys(activeSinkMetrics).length > 0
  const sourceFrames = runOnceMetrics.source_frame_count || 0
  const sourceSymbols = runOnceMetrics.source_symbol_count || 0
  const sourceTheoryMetrics = activeSinkMetrics.source_entropy !== undefined ? activeSinkMetrics : sourceFrames ? {
    source_entropy: runOnceMetrics.source_entropy_sum / sourceFrames,
    source_max_entropy: runOnceMetrics.source_max_entropy_sum / sourceFrames,
    source_efficiency_percent: runOnceMetrics.source_efficiency_sum / sourceFrames,
    source_average_information: sourceSymbols ? runOnceMetrics.source_information_sum / sourceSymbols : 0,
    source_alphabet_size: runOnceMetrics.source_alphabet_size_peak,
  } : undefined
  const symbolMetrics = activeSinkMetrics.ser !== undefined ? activeSinkMetrics : runOnceMetrics.total_symbols ? {
    ser: runOnceMetrics.symbol_errors / runOnceMetrics.total_symbols,
    symbol_errors: runOnceMetrics.symbol_errors,
    total_symbols: runOnceMetrics.total_symbols,
  } : undefined

  return (
    <div className="app-shell" style={{ gridTemplateRows: `60px minmax(0, 1fr) ${consoleOpen ? consoleHeight : 0}px`, gridTemplateColumns: `${leftOpen ? leftWidth : 0}px minmax(0, 1fr) ${rightOpen ? rightWidth : 0}px` }}>
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><img src="/app-icon.svg" alt="SignalLab logo" /></div><div><strong>SignalLab</strong><span>Communications Studio</span></div></div>
        <div className={`project-name ${projectDirty ? 'dirty' : ''}`} title={projectDirty ? 'Unsaved changes' : 'All changes saved'}><span className="status-dot" /><span>{projectName}</span>{projectDirty && <small>Unsaved</small>}</div>
        <div className="top-actions">
          <button className="ghost" onClick={() => setLeftOpen(value => !value)} title={leftOpen ? 'Hide block library' : 'Show block library'}><PanelLeft size={16} /></button>
          <button className="ghost" onClick={() => setRightOpen(value => !value)} title={rightOpen ? 'Hide inspector' : 'Show inspector'}><PanelRight size={16} /></button>
          <button className={`ghost ${consoleOpen ? 'active' : ''}`} onClick={() => setConsoleOpen(value => !value)} title={consoleOpen ? 'Hide console' : 'Show console'}><PanelBottom size={16} /></button>
          <button className="ghost" onClick={resetSample} title="Reset sample"><RotateCcw size={16} /></button>
          <button className="ghost labeled compact-label" onClick={newSimulation} disabled={executionActive} title="Create a blank simulation"><FilePlus2 size={15} /><span>New</span></button>
          <button className="ghost labeled compact-label" onClick={() => void openProject()} title="Open a SignalLab simulation"><FolderOpen size={15} /><span>Open</span></button>
          <button className="ghost labeled samples-action" onClick={() => setSamplesOpen(true)} title="Open a complete learning sample"><LibraryBig size={15} /><span>Open Samples</span></button>
          <input ref={fileRef} type="file" accept=".slab.json,.json,application/json" hidden onChange={e => { void importProject(e.target.files?.[0]); e.target.value = '' }} />
          <button className="ghost labeled save-action compact-label" onClick={() => void saveProject(false)} disabled={savingProject} title="Save simulation (Ctrl+S)"><Save size={15} /><span>{savingProject ? 'Saving…' : 'Save'}</span></button>
          <button className="ghost labeled compact-label" onClick={() => void saveProject(true)} disabled={savingProject} title="Save simulation as a new file (Ctrl+Shift+S)"><SaveAll size={15} /><span>Save As</span></button>
          <button className="ghost labeled documents-action" onClick={openDocuments} title="Open SignalLab documentation in a separate window"><BookOpen size={15} /><span>Documents</span></button>
        </div>
      </header>
      <SampleLibraryModal open={samplesOpen} onClose={() => setSamplesOpen(false)} onOpenSample={openCatalogSample} />
      {pythonEditorOpen && selected?.data.blockType === 'python' && <Suspense fallback={null}><PythonEditorModal
        open={pythonEditorOpen && selected?.data.blockType === 'python'}
        blockName={selected?.data.label || 'Python Block'}
        value={selected?.data.code || pythonTemplate}
        template={pythonTemplate}
        onApply={updatePythonCode}
        onClose={() => setPythonEditorOpen(false)}
        onOpenDocs={openDocuments}
      /></Suspense>}

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
        <ReactFlow nodes={nodes} edges={edges.map(e => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed }, animated: job?.status === 'running' }))} nodeTypes={{ signal: SignalNode }} onNodesChange={onNodesChange} onEdgesChange={onEdgesChangeWithPreview} onConnect={onConnect} onNodeClick={onNodeClick} onNodeDragStart={onNodeDragStart} onPaneClick={() => setSelectedId(null)} fitView minZoom={0.2} maxZoom={2} defaultEdgeOptions={{ style: { strokeWidth: 2, stroke: '#7d8998' } }}>
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#ccd3dc" />
          <Controls position="bottom-left" />
          <MiniMap position="bottom-right" pannable zoomable offsetScale={4} nodeColor={node => miniMapColor(String((node.data as Record<string, unknown>)?.blockType || ''))} nodeStrokeColor="#ffffff" nodeStrokeWidth={1} nodeBorderRadius={3} nodeComponent={FlowMiniMapNode} bgColor="#f9fbfd" maskColor="rgba(226,233,242,.62)" maskStrokeColor="#8ea8ca" maskStrokeWidth={1} style={{ width: 150, height: 92, border: '1px solid #cbd6e3', borderRadius: 8, boxShadow: '0 3px 12px rgba(36,55,78,.14)' }} />
        </ReactFlow>
      </main>

      <aside className={`inspector ${rightOpen ? '' : 'collapsed'}`}>
        <div className="tabs"><button className={rightTab === 'run' ? 'active' : ''} onClick={() => setRightTab('run')}>Experiment</button><button className={rightTab === 'block' ? 'active' : ''} onClick={() => setRightTab('block')}>Block</button></div>
        {rightTab === 'block' ? selected ? <div className="inspector-content">
          <div className="selection-heading"><span className="large-icon">{selected.data.blockType === 'python' ? <Braces /> : <Box />}</span><div><small>SELECTED BLOCK</small><h3>{selected.data.label}</h3></div><button className="icon-danger" onClick={() => { setNodes(ns => ns.filter(n => n.id !== selected.id).map(n => ({ ...n, data: { ...n.data, portPreviews: undefined, runtimeError: undefined } }))); setEdges(es => es.filter(e => e.source !== selected.id && e.target !== selected.id)); setSelectedId(null) }}><X size={16} /></button></div>
          {selected.data.runtimeError && <div className="error-box"><strong>Signal size contract failed</strong><br />{selected.data.runtimeError}</div>}
          {selectedSpec?.size_contract && <div className="signal-contract"><strong>Signal size contract</strong><span>{selectedSpec.size_contract}</span></div>}
          <label>Display name<input value={selected.data.label} onChange={e => updateSelected({ label: e.target.value })} /></label>
           <div className="port-layout-control"><div><span>Port layout</span><small>{selected.data.portOrientation === 'reversed' ? 'Input right · Output left' : 'Input left · Output right'}</small></div><button className={`port-toggle ${selected.data.portOrientation === 'reversed' ? 'active' : ''}`} onClick={() => updateSelected({ portOrientation: selected.data.portOrientation === 'reversed' ? 'standard' : 'reversed' })}><ArrowLeftRight size={15} /> {selected.data.portOrientation === 'reversed' ? 'Reversed' : 'Standard'}</button></div>
           <div className="section-rule"><span>PARAMETERS</span></div>
           {selectedIsFileSource && <label>Input file<input type="file" accept={selected.data.blockType === 'image_file_source' ? 'image/*' : '.txt,.csv,.log,text/plain'} onChange={loadSourceFile} /><small>{String(selected.data.params.file_name || 'No file selected')}</small></label>}
           {selectedIsStochasticChannel && <label>SNR source<select value={String(selected.data.params.snr_mode || 'experiment')} onChange={e => updateSelected({ params: { ...selected.data.params, snr_mode: e.target.value } })}><option value="experiment">Experiment sweep</option><option value="fixed">Fixed block value</option></select></label>}
           {selectedIsStochasticChannel && String(selected.data.params.snr_mode || 'experiment') === 'fixed' && <label>Fixed SNR dB<input type="number" value={String(selected.data.params.ebn0_db ?? 4)} onChange={e => updateSelected({ params: { ...selected.data.params, ebn0_db: Number(e.target.value) } })} /></label>}
           {selected.data.blockType === 'image_file_source' && <label>Pixel mode<select value={String(selected.data.params.mode || 'grayscale')} onChange={e => updateSelected({ params: { ...selected.data.params, mode: e.target.value } })}><option value="grayscale">Grayscale</option><option value="rgb">RGB</option></select></label>}
           {visibleParams.length ? visibleParams.map(([key, value]) => typeof value === 'boolean' ? <label className="boolean-param" key={key}><span>{parameterLabel(key)}</span><input type="checkbox" checked={value} onChange={e => updateSelected({ params: { ...selected.data.params, [key]: e.target.checked } })} />{key === 'include_header' && <small>Enable the same option on the matching decoder.</small>}</label> : <label key={key}>{parameterLabel(key)}<input type={typeof value === 'number' ? 'number' : 'text'} value={String(value)} onChange={e => updateSelected({ params: { ...selected.data.params, [key]: typeof value === 'number' ? Number(e.target.value) : e.target.value } })} />{key === 'seed' && <small>-1 = random each run · 0+ = reproducible</small>}</label>) : !['variables', 'awgn', 'rayleigh', 'text_file_source', 'image_file_source'].includes(selected.data.blockType) && <p className="muted">This block has no parameters.</p>}
          {selected.data.blockType === 'variables' && <VariablesEditor definitions={String(selected.data.params.definitions || '')} onChange={definitions => updateSelected({ params: { ...selected.data.params, definitions } })} />}
          {selected.data.blockType === 'symbol_huffman_encode' && <><div className="section-rule"><span>CURRENT HUFFMAN CODEBOOK</span><em>updates with P(x)</em></div><HuffmanCodebookTable params={selected.data.params} inputPreview={selected.data.portPreviews?.inputs.in} /></>}
          <div className="section-rule"><span>CURRENT PORT DATA</span><em>representative frame</em></div>
          <PortDataInspector snapshotId={snapshotId} nodeId={selected.id} previews={selected.data.portPreviews} />
          {selected.data.blockType === 'ber' && livePoints.length ? <><div className="section-rule"><span>SINK PREVIEW</span></div><BerChart points={livePoints} live={job?.status === 'running'} /></> : null}
          {activeSinkMetrics.power_mean !== undefined && selected.data.blockType === 'power_meter' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean power</span><strong>{activeSinkMetrics.power_mean.toExponential(3)}</strong></div></div></>}
          {activeSinkMetrics.scope_mean_amplitude !== undefined && selected.data.blockType === 'scope' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean amplitude</span><strong>{activeSinkMetrics.scope_mean_amplitude.toFixed(4)}</strong></div><div><span>Peak</span><strong>{activeSinkMetrics.scope_peak_amplitude?.toFixed(4) ?? '—'}</strong></div></div></>}
          {activeSinkMetrics.constellation_mean_i !== undefined && selected.data.blockType === 'constellation' && <><div className="section-rule"><span>SINK RESULT</span></div><div className="sink-result"><Activity size={18} /><div><span>Mean I / Q</span><strong>{`${activeSinkMetrics.constellation_mean_i.toFixed(3)} / ${activeSinkMetrics.constellation_mean_q.toFixed(3)}`}</strong></div><div><span>Mean |x|</span><strong>{activeSinkMetrics.constellation_mean_power?.toFixed(4) ?? '—'}</strong></div></div></>}
          {sourceTheoryMetrics && selected.data.blockType === 'source_analyzer' && <><div className="section-rule"><span>SOURCE THEORY RESULTS</span></div><div className="source-theory-result"><div><span>Entropy H(X)</span><strong>{sourceTheoryMetrics.source_entropy?.toFixed(4)} bit/symbol</strong></div><div><span>Average information</span><strong>{sourceTheoryMetrics.source_average_information?.toFixed(4)} bit/symbol</strong></div><div><span>Maximum entropy</span><strong>{sourceTheoryMetrics.source_max_entropy?.toFixed(4)} bit/symbol</strong></div><div><span>Source efficiency</span><strong>{sourceTheoryMetrics.source_efficiency_percent?.toFixed(2)}%</strong></div><div><span>Alphabet size</span><strong>{sourceTheoryMetrics.source_alphabet_size}</strong></div></div></>}
          {symbolMetrics && selected.data.blockType === 'ser' && <><div className="section-rule"><span>SYMBOL RESULT</span></div><div className="source-theory-result"><div><span>Symbol error rate</span><strong>{symbolMetrics.ser?.toExponential(3)}</strong></div><div><span>Symbol errors</span><strong>{symbolMetrics.symbol_errors} / {symbolMetrics.total_symbols}</strong></div></div></>}
          {selected.data.blockType === 'python' && <><div className="section-rule"><span>PYTHON PROCESSOR</span><em>trusted local code</em></div><div className="python-editor-inline-toolbar"><div><Braces size={14} /><span><b>process.py</b><small>Python 3 · UTF-8</small></span></div><button type="button" onClick={() => setPythonEditorOpen(true)}><Maximize2 size={14} /> Open editor</button></div><Suspense fallback={<div className="python-editor-loading">Loading Python editor…</div>}><PythonCodeEditor value={selected.data.code || pythonTemplate} onChange={updatePythonCode} /></Suspense><p className="code-hint">Read the current sweep point with <code>params["snr_db"]</code>. For flexible ports, declare <code>PORTS = {'{'}"inputs": ["signal", "noise"], "outputs": ["out", "residual"]{'}'}</code> and write <code>process(inputs, params)</code> returning a dictionary. <button type="button" onClick={openDocuments}>Read Python API</button></p></>}
        </div> : <div className="empty-state"><Box size={32} /><h3>No block selected</h3><p>Select a block on the canvas to edit its parameters and Python code.</p></div> :
        <div className="inspector-content">
          <div className="experiment-title"><div><small>MONTE-CARLO</small><h2>Experiment</h2></div><button className="run-once" onClick={runOnce} disabled={executionActive || Boolean(configIssue)} title="Execute one frame and capture data at every port"><Play size={13} fill="currentColor" />{runOnceActive ? 'Running…' : 'Run once'}</button></div>
          <div className="section-rule"><span>SNR SWEEP (dB)</span></div>
          <div className="form-grid"><label>Start<input disabled={executionActive} type="number" step="any" value={config.snr_db_start} onChange={e => setConfig({ ...config, snr_db_start: Number(e.target.value) })} /></label><label>Stop<input disabled={executionActive} type="number" step="any" value={config.snr_db_stop} onChange={e => setConfig({ ...config, snr_db_stop: Number(e.target.value) })} /></label></div>
          <div className="form-grid"><label>Step<input disabled={executionActive} type="number" min="0.01" step="any" value={config.snr_db_step} onChange={e => setConfig({ ...config, snr_db_step: Number(e.target.value) })} /></label><label>Max frames / SNR<input disabled={executionActive} type="number" min="1" value={config.max_frames} onChange={e => { const value = Number(e.target.value); setConfig({ ...config, max_frames: value, trials: value }) }} /></label></div>
          <div className="form-grid"><label>Min frames / SNR<input disabled={executionActive} type="number" min="1" value={config.min_frames} onChange={e => setConfig({ ...config, min_frames: Number(e.target.value) })} /></label><label>Min errors / SNR<input disabled={executionActive} type="number" min="0" value={config.min_errors} onChange={e => setConfig({ ...config, min_errors: Number(e.target.value) })} /></label></div>
          <div className="section-rule"><span>RUNTIME</span></div>
          <div className="form-grid"><label>Workers<input disabled={executionActive} type="number" min="0" value={config.workers} onChange={e => setConfig({ ...config, workers: Number(e.target.value) })} /><small>0 = auto</small></label><label>Seed<input disabled={executionActive} type="number" value={config.seed} onChange={e => setConfig({ ...config, seed: Number(e.target.value) })} /></label></div>
          <label>Chunk size<input disabled={executionActive} type="number" min="1" value={config.chunk_size} onChange={e => setConfig({ ...config, chunk_size: Number(e.target.value) })} /></label>
          <label>Compute device<select disabled={executionActive} value={config.device} onChange={e => setConfig({ ...config, device: e.target.value as SimulationConfig['device'] })}><option value="auto">Auto · best available</option><option value="cpu">CPU · multiprocessing</option><option value="gpu">GPU · CUDA/CuPy</option></select></label>
          {configIssue && <div className="config-issue" role="alert">{configIssue}</div>}
          <button className="run-wide" onClick={runBenchmark} disabled={executionActive || Boolean(configIssue)} title={configIssue || undefined}><Play size={16} fill="currentColor" /> {jobActive ? 'Benchmark running…' : 'Run Benchmark'}</button>
          {job && <div className="job-card"><div className="job-line"><span><i className={`job-dot ${job.status}`} />{job.status}</span><b>{Math.round((job.progress || 0) * 100)}%</b></div><div className="progress"><span style={{ width: `${(job.progress || 0) * 100}%` }} /></div><div className="job-meta"><span>{job.completed_trials || 0} frames processed · {job.trials} max</span><span>{job.device || result?.device || 'preparing'}</span></div>{job.status === 'running' && <button className="cancel" onClick={() => cancelJob(job.id)}><CircleStop size={14} /> Cancel</button>}</div>}
          {error && <div className="error-box">{error}</div>}
          {((hasBerSink && (result || livePoints.length > 0)) || hasSinkResults) && <div className="results" ref={resultsRef}>
            <div className="section-rule"><span>{job?.status === 'running' ? 'LIVE RESULTS' : 'RESULTS'}</span></div>
            {hasBerSink && <><div className="ber-plot-section"><BerChart points={livePoints} live={job?.status === 'running'} /></div><ResultsTable points={livePoints} /></>}
            <SinkResults nodes={sinkNodes} metrics={activeSinkMetrics} />
            {result && <><div className="metric-row"><div className="metric"><span>Elapsed</span><strong>{result.elapsed_seconds.toFixed(2)} s</strong></div><div className="metric"><span>Throughput</span><strong>{formatNumber(result.throughput_bps / 1000)} kb/s</strong></div></div>{result.warnings?.map(w => <p className="warning" key={w}>{w}</p>)}</>}
          </div>}
        </div>}
        {rightOpen && <div className="sidebar-resizer right-resizer" onPointerDown={event => startResize('right', event)} title="Resize inspector" />}
      </aside>

      {consoleOpen && <section className="console-dock">
        <div className="console-resizer" onPointerDown={startConsoleResize} title="Resize console" />
        <div className="console-header"><div><Terminal size={15} /><strong>Console</strong><span>{consoleEntries.length} events</span></div><div className="console-actions"><button className="console-copy" onClick={() => void copyConsole()} disabled={!consoleEntries.length} title="Copy all console text"><Copy size={13} />{consoleCopied ? 'Copied' : 'Copy'}</button><button className="console-clear" onClick={() => setConsoleEntries([])} title="Clear console"><Trash2 size={14} /></button></div></div>
        <div className="console-body">
          {consoleEntries.length ? consoleEntries.map(entry => <div className={`console-line ${entry.level}`} key={entry.id}><time>{entry.time}</time><b>{entry.level}</b><span>{entry.message}</span></div>) : <div className="console-empty">No messages yet.</div>}
        </div>
      </section>}
    </div>
  )
}

export default App
