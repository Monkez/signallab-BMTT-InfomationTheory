import type { FlowEdge, FlowNode, Job, SimulationConfig } from './types'

const graphPayload = (nodes: FlowNode[], edges: FlowEdge[]) => ({
  version: '1.0',
  nodes: nodes.map(n => ({
    id: n.id, type: n.data.blockType, label: n.data.label, position: n.position,
    params: n.data.params, code: n.data.code,
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
    const body = await response.json()
    throw new Error(Array.isArray(body.detail) ? body.detail.join(' · ') : body.detail || 'Could not start simulation')
  }
  return (await response.json()).job_id as string
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

