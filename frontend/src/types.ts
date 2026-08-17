import type { Edge, Node } from '@xyflow/react'

export type BlockData = {
  label: string
  blockType: string
  category: string
  params: Record<string, string | number | boolean>
  code?: string
  inputs: string[]
  outputs: string[]
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
  }
}

