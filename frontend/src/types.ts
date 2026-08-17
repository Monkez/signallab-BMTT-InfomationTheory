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
  [key: string]: unknown
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
  device?: string
  workers?: number
  result?: {
    bit_errors: number
    total_bits: number
    ber: number | null
    elapsed_seconds: number
    throughput_bps: number
    device: string
    workers: number
    warnings: string[]
    snr_points: Array<{
      snr_db: number
      bit_errors: number
      total_bits: number
      frames: number
      ber: number | null
    }>
  }
}
