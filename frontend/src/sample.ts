import type { FlowEdge, FlowNode } from './types'

const block = (id: string, blockType: string, label: string, x: number, y: number, inputs: string[], outputs: string[], params = {}): FlowNode => ({
  id, type: 'signal', position: { x, y }, data: { label, blockType, category: '', params, inputs, outputs },
})

export const initialNodes: FlowNode[] = [
  block('source', 'bit_source', 'Random bits', 40, 190, [], ['out'], { length: 4096 }),
  block('encoder', 'hamming74_encode', 'Hamming 7,4', 270, 190, ['in'], ['out', 'reference']),
  block('mod', 'bpsk_mod', 'BPSK', 500, 190, ['in'], ['out']),
  block('channel', 'awgn', 'AWGN', 700, 190, ['in'], ['out'], { ebn0_db: 4, snr_mode: 'experiment' }),
  block('demod', 'bpsk_demod', 'Hard decision', 900, 190, ['in'], ['out']),
  block('decoder', 'hamming74_decode', 'Hamming decode', 1110, 190, ['in'], ['out']),
  block('meter', 'ber', 'BER meter', 1340, 190, ['reference', 'estimate'], []),
]

export const initialEdges: FlowEdge[] = [
  { id: 'e1', source: 'source', target: 'encoder', sourceHandle: 'out', targetHandle: 'in' },
  { id: 'e2', source: 'encoder', target: 'mod', sourceHandle: 'out', targetHandle: 'in' },
  { id: 'e3', source: 'mod', target: 'channel', sourceHandle: 'out', targetHandle: 'in' },
  { id: 'e4', source: 'channel', target: 'demod', sourceHandle: 'out', targetHandle: 'in' },
  { id: 'e5', source: 'demod', target: 'decoder', sourceHandle: 'out', targetHandle: 'in' },
  { id: 'e6', source: 'encoder', target: 'meter', sourceHandle: 'reference', targetHandle: 'reference' },
  { id: 'e7', source: 'decoder', target: 'meter', sourceHandle: 'out', targetHandle: 'estimate' },
]

export const pythonTemplate = `# NumPy is available as np. Use context.xp for NumPy/CuPy portable code.
def process(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"])
    gain = float(params.get("gain", 1.0))
    return {"out": samples * gain}
`
