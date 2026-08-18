from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SIZE_CONTRACTS = {
    "bit_source": "out = length values; seed = -1 is random each run",
    "text_source": "out = reference = UTF-8 bits × repeat",
    "text_file_source": "out = reference = file bits × repeat",
    "text_symbol_source": "out = Unicode character symbols × repeat",
    "text_file_symbol_source": "out = UTF-8 file characters × repeat",
    "discrete_symbol_source": "out = length random symbols drawn from configured P(x)",
    "source_analyzer": "symbols, probability and information outputs each match input size",
    "symbols_to_bits": "out = reference = UTF-8 bits of the input symbols",
    "image_file_source": "out = reference = pixel bits",
    "differential_encode": "out = in",
    "differential_decode": "out = in",
    "huffman_encode": "reference = in; out is variable-length with a 32-bit size header",
    "huffman_decode": "out must match the size declared by the input header",
    "shannon_fano_encode": "reference = in; out is variable-length with a 32-bit size header",
    "shannon_fano_decode": "out must match the size declared by the input header",
    "symbol_huffman_encode": "reference = input symbols; out is a variable-length bitstream with symbol-count header",
    "symbol_huffman_decode": "out symbols must match the count declared by the bitstream header",
    "symbol_shannon_fano_encode": "reference = input symbols; out is a variable-length bitstream with symbol-count header",
    "symbol_shannon_fano_decode": "out symbols must match the count declared by the bitstream header",
    "rle_encode": "reference = in; out contains complete 9-bit count/value groups",
    "rle_decode": "in must be divisible by 9; out must match the encoded run counts",
    "zip_encode": "reference = in; out contains a 32-bit size header and DEFLATE payload",
    "zip_decode": "out must match the size declared by the input header",
    "hamming74_encode": "in must be divisible by 4; out = in × 7/4; reference = in",
    "hamming74_decode": "in must be divisible by 7; out = in × 4/7",
    "repetition3_encode": "out = in × 3; reference = in",
    "repetition3_decode": "in must be divisible by 3; out = in / 3",
    "bpsk_mod": "out = in",
    "qpsk_mod": "in must be even; out = in / 2 complex symbols",
    "awgn": "out = in; seed = -1 is random each run",
    "rayleigh": "out = in; seed = -1 is random each run",
    "bpsk_demod": "out = in",
    "qpsk_demod": "out = in × 2 bits",
    "scope": "in must be a non-empty 1-D signal",
    "constellation": "in must be a non-empty 1-D signal",
    "power_meter": "in must be a non-empty 1-D signal",
    "ber": "reference and estimate must have exactly the same size",
    "ser": "reference and estimate must contain the same number of symbols",
    "python": "out follows output_size: same (default), any, or an exact positive length",
}


@dataclass(frozen=True)
class BlockSpec:
    type: str
    label: str
    category: str
    description: str
    defaults: dict[str, Any]
    inputs: list[str]
    outputs: list[str]
    gpu_compatible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "size_contract": SIZE_CONTRACTS.get(self.type, "All ports must be non-empty 1-D signals")}


SPECS = [
    BlockSpec("bit_source", "Bit Source", "Sources", "Generate random binary messages; seed -1 is random each run.", {"length": 4096, "seed": -1}, [], ["out"]),
    BlockSpec("text_source", "Text Source", "Sources", "Convert UTF-8 text into a repeatable bit stream.", {"text": "HELLO", "repeat": 1}, [], ["out", "reference"]),
    BlockSpec("text_file_source", "Text File Source", "Sources", "Load a UTF-8/text file and emit its bytes as bits.", {"file_name": "", "data_base64": "", "repeat": 1}, [], ["out", "reference"], False),
    BlockSpec("text_symbol_source", "Text Symbol Source", "Source theory", "Emit text as visible Unicode character symbols.", {"text": "ABACABAD", "repeat": 1}, [], ["out"], False),
    BlockSpec("text_file_symbol_source", "Text File Symbols", "Source theory", "Load a UTF-8 file and emit visible character symbols.", {"file_name": "", "data_base64": "", "repeat": 1}, [], ["out"], False),
    BlockSpec("discrete_symbol_source", "Discrete Symbol Source", "Source theory", "Generate symbols from a configurable alphabet and probability model.", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125", "length": 100, "seed": -1}, [], ["out"], False),
    BlockSpec("source_analyzer", "Source Information Analyzer", "Source theory", "Measure P(x), self-information, entropy and source efficiency.", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}, ["in"], ["symbols", "probability", "information"], False),
    BlockSpec("symbols_to_bits", "Symbols to UTF-8 Bits", "Source theory", "Convert symbol text to a binary UTF-8 stream before channel coding.", {"separator": ""}, ["in"], ["out", "reference"], False),
    BlockSpec("image_file_source", "Image File Source", "Sources", "Load an image and emit grayscale or RGB pixel bits.", {"file_name": "", "data_base64": "", "mode": "grayscale"}, [], ["out", "reference"], False),
    BlockSpec("differential_encode", "Differential Encoder", "Source coding", "Cumulative XOR transform for a binary stream.", {}, ["in"], ["out"]),
    BlockSpec("differential_decode", "Differential Decoder", "Source coding", "Invert a differential binary stream.", {}, ["in"], ["out"]),
    BlockSpec("huffman_encode", "Huffman Encoder", "Source coding", "Pedagogical fixed 2-bit-symbol Huffman encoder.", {"weights": "8,4,2,1"}, ["in"], ["out", "reference"], False),
    BlockSpec("huffman_decode", "Huffman Decoder", "Source coding", "Decode the matching fixed Huffman codebook.", {"weights": "8,4,2,1"}, ["in"], ["out"], False),
    BlockSpec("shannon_fano_encode", "Shannon-Fano Encoder", "Source coding", "Pedagogical Shannon-Fano encoder for 2-bit symbols.", {"weights": "8,4,2,1"}, ["in"], ["out", "reference"], False),
    BlockSpec("shannon_fano_decode", "Shannon-Fano Decoder", "Source coding", "Decode the matching Shannon-Fano codebook.", {"weights": "8,4,2,1"}, ["in"], ["out"], False),
    BlockSpec("symbol_huffman_encode", "Huffman Symbol Encoder", "Source theory", "Huffman-code text symbols using configurable P(x).", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}, ["in"], ["out", "reference"], False),
    BlockSpec("symbol_huffman_decode", "Huffman Symbol Decoder", "Source theory", "Recover text symbols with the matching Huffman model.", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}, ["in"], ["out"], False),
    BlockSpec("symbol_shannon_fano_encode", "Shannon-Fano Symbol Encoder", "Source theory", "Shannon-Fano-code text symbols using configurable P(x).", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}, ["in"], ["out", "reference"], False),
    BlockSpec("symbol_shannon_fano_decode", "Shannon-Fano Symbol Decoder", "Source theory", "Recover text symbols with the matching Shannon-Fano model.", {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}, ["in"], ["out"], False),
    BlockSpec("rle_encode", "Run-Length Encoder", "Source coding", "Encode binary runs as 8-bit count plus value.", {}, ["in"], ["out", "reference"], False),
    BlockSpec("rle_decode", "Run-Length Decoder", "Source coding", "Decode binary run-length pairs.", {}, ["in"], ["out"], False),
    BlockSpec("zip_encode", "ZIP (DEFLATE) Encoder", "Source coding", "Compress a bitstream with the standard DEFLATE codec.", {}, ["in"], ["out", "reference"], False),
    BlockSpec("zip_decode", "ZIP (DEFLATE) Decoder", "Source coding", "Decompress a bitstream encoded by ZIP Encoder.", {}, ["in"], ["out"], False),
    BlockSpec("hamming74_encode", "Hamming (7,4) Encoder", "Channel coding", "Systematic encoding: [d1 d2 d3 d4 p1 p2 p3].", {}, ["in"], ["out", "reference"]),
    BlockSpec("repetition3_encode", "Repetition-3 Encoder", "Channel coding", "Repeat each bit three times.", {}, ["in"], ["out", "reference"]),
    BlockSpec("repetition3_decode", "Repetition-3 Decoder", "Channel coding", "Majority decode groups of three bits.", {}, ["in"], ["out"]),
    BlockSpec("bpsk_mod", "BPSK Modulator", "Modulation", "Map 0 → +1 and 1 → -1.", {}, ["in"], ["out"]),
    BlockSpec("qpsk_mod", "QPSK Modulator", "Modulation", "Gray-free QPSK mapping of bit pairs.", {}, ["in"], ["out"]),
    BlockSpec("awgn", "AWGN Channel", "Channels", "Add seeded noise; seed -1 is random each run.", {"ebn0_db": 4.0, "snr_mode": "experiment", "seed": -1}, ["in"], ["out"]),
    BlockSpec("rayleigh", "Rayleigh Fading", "Channels", "Seeded flat fading plus noise; seed -1 is random each run.", {"ebn0_db": 4.0, "snr_mode": "experiment", "seed": -1}, ["in"], ["out"], False),
    BlockSpec("bpsk_demod", "BPSK Demodulator", "Receivers", "Hard-decision BPSK detector.", {}, ["in"], ["out"]),
    BlockSpec("qpsk_demod", "QPSK Demodulator", "Receivers", "Hard-decision QPSK detector.", {}, ["in"], ["out"]),
    BlockSpec("hamming74_decode", "Hamming (7,4) Decoder", "Channel coding", "Decode systematic [data parity] words and correct one bit.", {}, ["in"], ["out"]),
    BlockSpec("scope", "Signal Scope", "Sinks", "Summarize amplitude and power of a signal.", {}, ["in"], []),
    BlockSpec("constellation", "Constellation Sink", "Sinks", "Summarize I/Q samples for constellation inspection.", {}, ["in"], []),
    BlockSpec("power_meter", "Power Meter", "Sinks", "Measure mean signal power.", {}, ["in"], []),
    BlockSpec("ber", "BER Meter", "Sinks", "Compare received bits with a reference stream.", {}, ["reference", "estimate"], []),
    BlockSpec("ser", "Symbol Error Rate", "Source theory", "Compare original and decoded text symbols.", {}, ["reference", "estimate"], [], False),
    BlockSpec("python", "Python Block", "Custom", "Write process(signal, params); the runtime handles trial parallelism.", {"gain": 1.0, "output_size": "same"}, ["in"], ["out"], False),
]

SPEC_BY_TYPE = {spec.type: spec for spec in SPECS}
