import { Activity, Binary, Box, Braces, Gauge, Radio, Waves, type LucideIcon } from 'lucide-react'
import type { BlockSpec } from '../../types'

/** Offline catalog used while the Python API starts. The backend registry remains authoritative. */
export const fallbackSpecs: BlockSpec[] = [
  { type: 'bit_source', label: 'Bit Source', category: 'Sources', description: 'Random binary messages', defaults: { length: 4096 }, inputs: [], outputs: ['out'], gpu_compatible: true },
  { type: 'text_source', label: 'Text Source', category: 'Sources', description: 'UTF-8 text to bits', defaults: { text: 'HELLO', repeat: 1 }, inputs: [], outputs: ['out', 'reference'], gpu_compatible: true },
  { type: 'text_file_source', label: 'Text File Source', category: 'Sources', description: 'Load a text file as bits', defaults: { file_name: '', data_base64: '', repeat: 1 }, inputs: [], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'image_file_source', label: 'Image File Source', category: 'Sources', description: 'Load image pixels as bits', defaults: { file_name: '', data_base64: '', mode: 'grayscale' }, inputs: [], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'differential_encode', label: 'Differential Encoder', category: 'Source coding', description: 'Cumulative XOR transform', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'differential_decode', label: 'Differential Decoder', category: 'Source coding', description: 'Invert differential bits', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'huffman_encode', label: 'Huffman Encoder', category: 'Source coding', description: 'Fixed 2-bit-symbol Huffman encoder', defaults: { weights: '8,4,2,1' }, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'huffman_decode', label: 'Huffman Decoder', category: 'Source coding', description: 'Decode Huffman stream', defaults: { weights: '8,4,2,1' }, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
  { type: 'shannon_fano_encode', label: 'Shannon-Fano Encoder', category: 'Source coding', description: 'Shannon-Fano source encoder', defaults: { weights: '8,4,2,1' }, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'shannon_fano_decode', label: 'Shannon-Fano Decoder', category: 'Source coding', description: 'Decode Shannon-Fano stream', defaults: { weights: '8,4,2,1' }, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
  { type: 'rle_encode', label: 'Run-Length Encoder', category: 'Source coding', description: 'Encode binary runs', defaults: {}, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'rle_decode', label: 'Run-Length Decoder', category: 'Source coding', description: 'Decode binary runs', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
  { type: 'zip_encode', label: 'ZIP (DEFLATE) Encoder', category: 'Source coding', description: 'Standard DEFLATE compression', defaults: {}, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: false },
  { type: 'zip_decode', label: 'ZIP (DEFLATE) Decoder', category: 'Source coding', description: 'Standard DEFLATE decompression', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
  { type: 'hamming74_encode', label: 'Hamming Encoder', category: 'Channel coding', description: 'Hamming (7,4)', defaults: {}, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: true },
  { type: 'repetition3_encode', label: 'Repetition-3 Encoder', category: 'Channel coding', description: 'Repeat each bit three times', defaults: {}, inputs: ['in'], outputs: ['out', 'reference'], gpu_compatible: true },
  { type: 'repetition3_decode', label: 'Repetition-3 Decoder', category: 'Channel coding', description: 'Majority decode triples', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'bpsk_mod', label: 'BPSK Modulator', category: 'Modulation', description: 'Binary phase shift keying', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'qpsk_mod', label: 'QPSK Modulator', category: 'Modulation', description: 'Map bit pairs to I/Q', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'awgn', label: 'AWGN Channel', category: 'Channels', description: 'Experiment SNR sweep or fixed SNR', defaults: { ebn0_db: 4, snr_mode: 'experiment' }, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'rayleigh', label: 'Rayleigh Fading', category: 'Channels', description: 'Flat fading plus noise', defaults: { ebn0_db: 4, snr_mode: 'experiment' }, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
  { type: 'bpsk_demod', label: 'BPSK Demodulator', category: 'Receivers', description: 'Hard decision', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'qpsk_demod', label: 'QPSK Demodulator', category: 'Receivers', description: 'Hard decision I/Q', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'hamming74_decode', label: 'Hamming Decoder', category: 'Channel coding', description: 'Correct one bit', defaults: {}, inputs: ['in'], outputs: ['out'], gpu_compatible: true },
  { type: 'scope', label: 'Signal Scope', category: 'Sinks', description: 'Amplitude and peak summary', defaults: {}, inputs: ['in'], outputs: [], gpu_compatible: true },
  { type: 'constellation', label: 'Constellation Sink', category: 'Sinks', description: 'I/Q sample summary', defaults: {}, inputs: ['in'], outputs: [], gpu_compatible: true },
  { type: 'power_meter', label: 'Power Meter', category: 'Sinks', description: 'Mean signal power', defaults: {}, inputs: ['in'], outputs: [], gpu_compatible: true },
  { type: 'ber', label: 'BER Meter', category: 'Sinks', description: 'Measure bit error rate', defaults: {}, inputs: ['reference', 'estimate'], outputs: [], gpu_compatible: true },
  { type: 'python', label: 'Python Block', category: 'Custom', description: 'Custom NumPy processing', defaults: { gain: 1 }, inputs: ['in'], outputs: ['out'], gpu_compatible: false },
]

export function iconFor(type: string): LucideIcon {
  return type.includes('source') ? Binary : type.includes('awgn') || type.includes('rayleigh') ? Waves : type.includes('bpsk') || type.includes('qpsk') ? Radio : type === 'ber' ? Gauge : type === 'scope' || type === 'constellation' || type === 'power_meter' ? Activity : type === 'python' ? Braces : Box
}

export function miniMapColor(type: string) {
  return type.includes('source') ? '#5b8def' : type.includes('encode') || type.includes('decode') ? '#8b72d9' : type.includes('mod') || type.includes('demod') ? '#e49a45' : type.includes('awgn') || type.includes('rayleigh') ? '#41a987' : type === 'ber' || type.includes('meter') || type === 'scope' || type === 'constellation' ? '#d26782' : type === 'python' ? '#65748b' : '#8493a8'
}
