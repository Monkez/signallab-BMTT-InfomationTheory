import type { Edge, Node } from '@xyflow/react'

export type BlockData = {
  label: string
  blockType: string
  category: string
  params: Record<string, string | number | boolean>
  code?: string
  inputs: string[]
  outputs: string[]
  portOrientation?: 'standard' | 'reversed'
  portPreviews?: NodePortPreviews
  runtimeError?: string
  [key: string]: unknown
}

export type PortPreview = {
  dtype: string
  shape: number[]
  size: number
  sample: string[]
  min?: number
  max?: number
  mean?: number
  stats_label?: string
}

export type NodePortPreviews = {
  inputs: Record<string, PortPreview>
  outputs: Record<string, PortPreview>
}

export type PortPreviewMap = Record<string, NodePortPreviews>

export type RunOnceResult = {
  device: string
  snr_db: number
  elapsed_seconds: number
  metrics: Record<string, number>
  sink_metrics: Record<string, number>
  port_previews: PortPreviewMap
  snapshot_id: string
  warnings: string[]
}

export type PortDataPage = {
  snapshot_id: string
  node_id: string
  direction: 'inputs' | 'outputs'
  port: string
  dtype: string
  shape: number[]
  total: number
  offset: number
  limit: number
  values: string[]
}

export type FlowNode = Node<BlockData, 'signal'>
export type FlowEdge = Edge

export type BlockSpec = {
  type: string
  label: string
  category: string
  description: string
  defaults: Record<string, string | number | boolean>
  inputs: string[]
  outputs: string[]
  gpu_compatible: boolean
  size_contract?: string
}

export type SimulationConfig = {
  trials: number
  max_frames: number
  min_frames: number
  min_errors: number
  snr_db_start: number
  snr_db_stop: number
  snr_db_step: number
  workers: number
  seed: number
  device: 'auto' | 'cpu' | 'gpu'
  chunk_size: number
}

export type Job = {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  completed_trials: number
  trials: number
  error?: string
  error_block_id?: string
  error_block_label?: string
  node_errors?: Record<string, string[]>
  device?: string
  workers?: number
  snr_db?: number
  snr_index?: number
  snr_count?: number
  snr_points?: Array<{
    snr_db: number
    bit_errors: number
    total_bits: number
    frames: number
    ber: number | null
  }>
  result?: {
    bit_errors: number
    total_bits: number
    ber: number | null
    elapsed_seconds: number
    throughput_bps: number
    device: string
    workers: number
    warnings: string[]
    sink_metrics: Record<string, number>
    port_previews: PortPreviewMap
    snapshot_id?: string
    snr_points: Array<{
      snr_db: number
      bit_errors: number
      total_bits: number
      frames: number
      ber: number | null
    }>
  }
}
