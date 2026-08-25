import { useEffect, type CSSProperties } from 'react'
import { Handle, Position, useUpdateNodeInternals, type NodeProps } from '@xyflow/react'
import { AlertTriangle, Binary, Braces, Radio, Waves, Gauge, Box } from 'lucide-react'
import type { FlowNode, PortPreview } from './types'

const icons: Record<string, typeof Box> = {
  bit_source: Binary, text_source: Binary, text_file_source: Binary, image_file_source: Binary,
  python: Braces, awgn: Waves, ber: Gauge,
  bpsk_mod: Radio, bpsk_demod: Radio, qpsk_mod: Radio, qpsk_demod: Radio,
  ook_mod: Radio, ook_demod: Radio, psk8_mod: Radio, psk8_demod: Radio, qam16_mod: Radio, qam16_demod: Radio,
}

const metric = (value?: number) => value === undefined ? '—' : Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < .001) ? value.toExponential(3) : value.toPrecision(4)

function PortTooltip({ direction, port, preview }: { direction: 'Input' | 'Output'; port: string; preview?: PortPreview }) {
  return <div className="port-tooltip" role="tooltip">
    <div className="port-tooltip-title"><span>{direction}</span><strong>{port}</strong></div>
    {preview ? <>
      <div className="port-tooltip-meta"><span>{preview.dtype}</span><span>{preview.shape.length ? `[${preview.shape.join(' × ')}]` : 'scalar'}</span><span>{preview.size.toLocaleString()} values</span></div>
      {preview.mean !== undefined && <div className="port-tooltip-stats"><span>min <b>{metric(preview.min)}</b></span><span>mean <b>{metric(preview.mean)}</b></span><span>max <b>{metric(preview.max)}</b></span></div>}
      <div className="port-tooltip-sample"><small>First samples</small><code>{preview.sample.length ? preview.sample.join(', ') : 'empty'}</code></div>
    </> : <div className="port-tooltip-empty">Run once or Run Benchmark to inspect this port.</div>}
  </div>
}

export function SignalNode({ id, data, selected }: NodeProps<FlowNode>) {
  const Icon = icons[data.blockType] || Box
  const reversed = data.portOrientation === 'reversed'
  const inputPosition = reversed ? Position.Right : Position.Left
  const outputPosition = reversed ? Position.Left : Position.Right
  const updateNodeInternals = useUpdateNodeInternals()
  const portStyle = (index: number, count: number): CSSProperties => ({ '--port-offset': `${(index - (count - 1) / 2) * 22}px` } as CSSProperties)

  useEffect(() => {
    // Handle positions are dynamic. React Flow needs an explicit measurement
    // refresh so existing edges follow the new side immediately.
    updateNodeInternals(id)
  }, [id, reversed, data.inputs.length, data.outputs.length, updateNodeInternals])

  return (
    <div className={`signal-node ${selected ? 'selected' : ''} ${reversed ? 'ports-reversed' : ''} ${data.runtimeError ? 'invalid' : ''}`} aria-invalid={Boolean(data.runtimeError)}>
      <div className="node-glow" />
      {data.runtimeError && <div className="node-error-badge" title={data.runtimeError}><AlertTriangle size={13} /> Contract error</div>}
      <div className="node-header"><span className="node-icon"><Icon size={15} /></span><span>{data.label}</span></div>
      <div className="node-type">{data.blockType.replaceAll('_', ' ')}</div>
      {data.inputs.map((port, index) => {
        const preview = data.portPreviews?.inputs[port]
        const hasData = Boolean(preview && preview.size > 0)
        return <div className={`port-label input ${hasData ? 'has-data' : ''}`} key={port} style={portStyle(index, data.inputs.length)} tabIndex={0}>
          <Handle className={hasData ? 'has-data' : ''} type="target" position={inputPosition} id={port} aria-label={`Input ${port}${hasData ? ' has data' : ' is empty'}`} />{port}<PortTooltip direction="Input" port={port} preview={preview} />
        </div>
      })}
      {data.outputs.map((port, index) => {
        const preview = data.portPreviews?.outputs[port]
        const hasData = Boolean(preview && preview.size > 0)
        return <div className={`port-label output ${hasData ? 'has-data' : ''}`} key={port} style={portStyle(index, data.outputs.length)} tabIndex={0}>
          {port}<Handle className={hasData ? 'has-data' : ''} type="source" position={outputPosition} id={port} aria-label={`Output ${port}${hasData ? ' has data' : ' is empty'}`} /><PortTooltip direction="Output" port={port} preview={preview} />
        </div>
      })}
    </div>
  )
}
