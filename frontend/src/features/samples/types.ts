import type { BlockSpec, FlowEdge, FlowNode, SimulationConfig } from '../../types'

export type SampleCategory = 'Digital communications' | 'Information theory' | 'Python labs'

export type SampleMetadata = {
  id: string
  title: string
  subtitle: string
  category: SampleCategory
  level: 'Cơ bản' | 'Trung cấp' | 'Nâng cao'
  duration_minutes: number
  summary: string
  concepts: string[]
  learning_objectives: string[]
  instructions: string[]
  expected_observations: string[]
  uses_python: boolean
}

export type SampleGraphNode = {
  id: string
  type: string
  label: string
  position: { x: number; y: number }
  params?: Record<string, string | number | boolean>
  code?: string
  port_orientation?: 'standard' | 'reversed'
}

export type SampleGraphEdge = {
  id: string
  source: string
  target: string
  source_handle?: string
  target_handle?: string
}

export type SampleProject = {
  format: 'signallab-simulation'
  version: '1.0'
  sample: SampleMetadata
  graph: { version: '1.0'; nodes: SampleGraphNode[]; edges: SampleGraphEdge[] }
  config: SimulationConfig
}

export function materializeSample(sample: SampleProject, specs: BlockSpec[]) {
  const specMap = new Map(specs.map(spec => [spec.type, spec]))
  const nodes: FlowNode[] = sample.graph.nodes.map(node => {
    const spec = specMap.get(node.type)
    return {
      id: node.id,
      type: 'signal',
      position: node.position,
      data: {
        label: node.label,
        blockType: node.type,
        category: spec?.category || '',
        params: { ...(spec?.defaults || {}), ...(node.params || {}) },
        code: node.code,
        portOrientation: node.port_orientation || 'standard',
        inputs: spec?.inputs || ['in'],
        outputs: spec?.outputs || ['out'],
      },
    }
  })
  const edges: FlowEdge[] = sample.graph.edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_handle || 'out',
    targetHandle: edge.target_handle || 'in',
  }))
  return { nodes, edges, config: { ...sample.config } }
}
