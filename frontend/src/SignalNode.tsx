import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Binary, Braces, Radio, Waves, Gauge, Box } from 'lucide-react'
import type { FlowNode } from './types'

const icons: Record<string, typeof Box> = {
  bit_source: Binary, python: Braces, awgn: Waves, ber: Gauge,
  bpsk_mod: Radio, bpsk_demod: Radio,
}

export function SignalNode({ data, selected }: NodeProps<FlowNode>) {
  const Icon = icons[data.blockType] || Box
  const reversed = data.portOrientation === 'reversed'
  const inputPosition = reversed ? Position.Right : Position.Left
  const outputPosition = reversed ? Position.Left : Position.Right
  return (
    <div className={`signal-node ${selected ? 'selected' : ''} ${reversed ? 'ports-reversed' : ''}`}>
      <div className="node-glow" />
      <div className="node-header"><span className="node-icon"><Icon size={15} /></span><span>{data.label}</span></div>
      <div className="node-type">{data.blockType.replaceAll('_', ' ')}</div>
      {data.inputs.map((port, index) => (
        <div className="port-label input" key={port} style={{ top: 52 + index * 22 }}>
          <Handle type="target" position={inputPosition} id={port} />{port}
        </div>
      ))}
      {data.outputs.map((port, index) => (
        <div className="port-label output" key={port} style={{ top: 52 + index * 22 }}>
          {port}<Handle type="source" position={outputPosition} id={port} />
        </div>
      ))}
    </div>
  )
}
