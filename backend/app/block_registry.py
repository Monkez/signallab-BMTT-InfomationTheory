from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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
        return asdict(self)


SPECS = [
    BlockSpec("bit_source", "Bit Source", "Sources", "Generate random binary messages.", {"length": 4096}, [], ["out"]),
    BlockSpec("text_source", "Text Source", "Sources", "Convert UTF-8 text into a repeatable bit stream.", {"text": "HELLO", "repeat": 1}, [], ["out", "reference"]),
    BlockSpec("text_file_source", "Text File Source", "Sources", "Load a UTF-8/text file and emit its bytes as bits.", {"file_name": "", "data_base64": "", "repeat": 1}, [], ["out", "reference"], False),
    BlockSpec("image_file_source", "Image File Source", "Sources", "Load an image and emit grayscale or RGB pixel bits.", {"file_name": "", "data_base64": "", "mode": "grayscale"}, [], ["out", "reference"], False),
    BlockSpec("differential_encode", "Differential Encoder", "Source coding", "Cumulative XOR transform for a binary stream.", {}, ["in"], ["out"]),
    BlockSpec("differential_decode", "Differential Decoder", "Source coding", "Invert a differential binary stream.", {}, ["in"], ["out"]),
    BlockSpec("huffman_encode", "Huffman Encoder", "Source coding", "Pedagogical fixed 2-bit-symbol Huffman encoder.", {"weights": "8,4,2,1"}, ["in"], ["out", "reference"], False),
    BlockSpec("huffman_decode", "Huffman Decoder", "Source coding", "Decode the matching fixed Huffman codebook.", {"weights": "8,4,2,1"}, ["in"], ["out"], False),
    BlockSpec("shannon_fano_encode", "Shannon-Fano Encoder", "Source coding", "Pedagogical Shannon-Fano encoder for 2-bit symbols.", {"weights": "8,4,2,1"}, ["in"], ["out", "reference"], False),
    BlockSpec("shannon_fano_decode", "Shannon-Fano Decoder", "Source coding", "Decode the matching Shannon-Fano codebook.", {"weights": "8,4,2,1"}, ["in"], ["out"], False),
    BlockSpec("rle_encode", "Run-Length Encoder", "Source coding", "Encode binary runs as 8-bit count plus value.", {}, ["in"], ["out", "reference"], False),
    BlockSpec("rle_decode", "Run-Length Decoder", "Source coding", "Decode binary run-length pairs.", {}, ["in"], ["out"], False),
    BlockSpec("zip_encode", "ZIP (DEFLATE) Encoder", "Source coding", "Compress a bitstream with the standard DEFLATE codec.", {}, ["in"], ["out", "reference"], False),
    BlockSpec("zip_decode", "ZIP (DEFLATE) Decoder", "Source coding", "Decompress a bitstream encoded by ZIP Encoder.", {}, ["in"], ["out"], False),
    BlockSpec("hamming74_encode", "Hamming (7,4) Encoder", "Channel coding", "Encode 4 data bits into a Hamming(7,4) codeword.", {}, ["in"], ["out", "reference"]),
    BlockSpec("repetition3_encode", "Repetition-3 Encoder", "Channel coding", "Repeat each bit three times.", {}, ["in"], ["out", "reference"]),
    BlockSpec("repetition3_decode", "Repetition-3 Decoder", "Channel coding", "Majority decode groups of three bits.", {}, ["in"], ["out"]),
    BlockSpec("bpsk_mod", "BPSK Modulator", "Modulation", "Map 0 → +1 and 1 → -1.", {}, ["in"], ["out"]),
    BlockSpec("qpsk_mod", "QPSK Modulator", "Modulation", "Gray-free QPSK mapping of bit pairs.", {}, ["in"], ["out"]),
    BlockSpec("awgn", "AWGN Channel", "Channels", "Add noise from the experiment SNR sweep or a fixed value.", {"ebn0_db": 4.0, "snr_mode": "experiment"}, ["in"], ["out"]),
    BlockSpec("rayleigh", "Rayleigh Fading", "Channels", "Flat Rayleigh fading with AWGN noise.", {"ebn0_db": 4.0, "snr_mode": "experiment"}, ["in"], ["out"], False),
    BlockSpec("bpsk_demod", "BPSK Demodulator", "Receivers", "Hard-decision BPSK detector.", {}, ["in"], ["out"]),
    BlockSpec("qpsk_demod", "QPSK Demodulator", "Receivers", "Hard-decision QPSK detector.", {}, ["in"], ["out"]),
    BlockSpec("hamming74_decode", "Hamming (7,4) Decoder", "Channel coding", "Syndrome decode and correct one bit per codeword.", {}, ["in"], ["out"]),
    BlockSpec("scope", "Signal Scope", "Sinks", "Summarize amplitude and power of a signal.", {}, ["in"], []),
    BlockSpec("constellation", "Constellation Sink", "Sinks", "Summarize I/Q samples for constellation inspection.", {}, ["in"], []),
    BlockSpec("power_meter", "Power Meter", "Sinks", "Measure mean signal power.", {}, ["in"], []),
    BlockSpec("ber", "BER Meter", "Sinks", "Compare received bits with a reference stream.", {}, ["reference", "estimate"], []),
    BlockSpec("python", "Python Block", "Custom", "Write process(signal, params); the runtime handles trial parallelism.", {"gain": 1.0}, ["in"], ["out"], False),
]

SPEC_BY_TYPE = {spec.type: spec for spec in SPECS}
