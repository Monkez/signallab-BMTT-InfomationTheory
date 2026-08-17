import type { FlowEdge, FlowNode, Job, RunOnceResult, SimulationConfig } from './types'

export class GraphApiError extends Error {
  nodeErrors: Record<string, string[]>

  constructor(message: string, nodeErrors: Record<string, string[]> = {}) {
    super(message)
    this.name = 'GraphApiError'
    this.nodeErrors = nodeErrors
  }
}

async function graphError(response: Response, fallback: string) {
  const body = await response.json().catch(() => ({}))
  const detail = body.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return new GraphApiError(detail.message || fallback, detail.node_errors || {})
  }
  return new GraphApiError(Array.isArray(detail) ? detail.join(' · ') : detail || fallback)
}

const graphPayload = (nodes: FlowNode[], edges: FlowEdge[]) => ({
  version: '1.0',
  nodes: nodes.map(n => ({
    id: n.id, type: n.data.blockType, label: n.data.label, position: n.position,
    params: n.data.params, code: n.data.code,
    port_orientation: n.data.portOrientation || 'standard',
  })),
  edges: edges.map(e => ({
    id: e.id, source: e.source, target: e.target,
    source_handle: e.sourceHandle || 'out', target_handle: e.targetHandle || 'in',
  })),
})

export async function createJob(nodes: FlowNode[], edges: FlowEdge[], config: SimulationConfig) {
  const response = await fetch('/api/jobs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph: graphPayload(nodes, edges), config }),
  })
  if (!response.ok) {
    throw await graphError(response, 'Could not create benchmark job')
  }
  return (await response.json()).job_id as string
}

export async function runGraphOnce(nodes: FlowNode[], edges: FlowEdge[], config: SimulationConfig): Promise<RunOnceResult> {
  const response = await fetch('/api/run-once', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph: graphPayload(nodes, edges), config }),
  })
  if (!response.ok) {
    throw await graphError(response, 'Could not run the graph')
  }
  return response.json()
}

export async function getJob(id: string): Promise<Job> {
  const response = await fetch(`/api/jobs/${id}`)
  if (!response.ok) throw new Error('Simulation job was not found')
  return response.json()
}

export async function cancelJob(id: string) {
  await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
}

export { graphPayload }
