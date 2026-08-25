import type { FlowEdge, FlowNode, Job, PortDataPage, RunOnceResult, SimulationConfig } from './types'

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
  return new GraphApiError(formatApiDetail(detail, fallback))
}

export function formatApiDetail(detail: unknown, fallback = 'Request failed'): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(item => {
      if (typeof item === 'string') return item
      if (!item || typeof item !== 'object') return String(item)
      const issue = item as { msg?: unknown; message?: unknown; loc?: unknown[] }
      const message = String(issue.msg || issue.message || 'Invalid value')
      const location = Array.isArray(issue.loc) ? issue.loc.filter(part => part !== 'body').join(' → ') : ''
      return location ? `${location}: ${message}` : message
    }).filter(Boolean)
    return messages.join(' · ') || fallback
  }
  if (detail && typeof detail === 'object') {
    const issue = detail as { message?: unknown; msg?: unknown }
    return String(issue.message || issue.msg || fallback)
  }
  return fallback
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

export async function getPortValues(snapshotId: string, nodeId: string, direction: 'inputs' | 'outputs', port: string, offset = 0, limit = 128): Promise<PortDataPage> {
  const [snapshot, node, portName] = [snapshotId, nodeId, port].map(encodeURIComponent)
  const response = await fetch(`/api/snapshots/${snapshot}/nodes/${node}/ports/${direction}/${portName}?offset=${offset}&limit=${limit}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(formatApiDetail(body.detail, 'Port data is no longer available; run the graph again'))
  }
  return response.json()
}

export async function cancelJob(id: string) {
  await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
}

export { graphPayload }
