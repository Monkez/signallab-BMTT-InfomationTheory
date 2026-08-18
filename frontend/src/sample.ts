import type { FlowEdge, FlowNode } from './types'

const block = (id: string, blockType: string, label: string, x: number, y: number, inputs: string[], outputs: string[], params = {}, portOrientation: 'standard' | 'reversed' = 'standard'): FlowNode => ({
  id, type: 'signal', position: { x, y }, data: { label, blockType, category: '', params, inputs, outputs, portOrientation },
})

export const initialNodes: FlowNode[] = [
  block('source', 'bit_source', 'Random bits', 20, 48, [], ['out'], { length: 4096, seed: -1 }),
  block('encoder', 'hamming74_encode', 'Hamming 7,4', 252, 48, ['in'], ['out', 'reference']),
  block('mod', 'bpsk_mod', 'BPSK', 484, 48, ['in'], ['out']),
  block('channel', 'awgn', 'AWGN', 716, 48, ['in'], ['out'], { ebn0_db: 4, snr_mode: 'experiment', seed: -1 }),
  block('demod', 'bpsk_demod', 'Hard decision', 702, 380, ['in'], ['out'], {}, 'reversed'),
  block('decoder', 'hamming74_decode', 'Hamming decode', 428, 380, ['in'], ['out'], {}, 'reversed'),
  block('meter', 'ber', 'BER meter', 104, 326, ['reference', 'estimate'], [], {}, 'reversed'),
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

export const pythonTemplate = `import numpy as np
import scipy as sp
import signallab as sl

# Write ordinary Python code for one signal frame.
# SignalLab runs separate Monte-Carlo frames in parallel for you.
def process(signal, params):
    # Runtime values change automatically at every SNR/frame:
    snr_db = float(params["snr_db"])
    trial_index = int(params["trial_index"])

    # Values declared by a Variables block are available both ways:
    # symbol_rate = params["symbol_rate"]
    # all_globals = params["variables"]
    gain = float(params.get("gain", 1.0))
    return sl.signals.normalize_power(signal * gain)
`
