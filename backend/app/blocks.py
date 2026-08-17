from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np


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


SPECS = [
    BlockSpec("bit_source", "Bit Source", "Sources", "Generate random binary messages.", {"length": 4096}, [], ["out"]),
    BlockSpec("text_source", "Text Source", "Sources", "Convert UTF-8 text into a repeatable bit stream.", {"text": "HELLO", "repeat": 1}, [], ["out", "reference"]),
    BlockSpec("differential_encode", "Differential Encoder", "Source coding", "Cumulative XOR transform for a binary stream.", {}, ["in"], ["out"]),
    BlockSpec("differential_decode", "Differential Decoder", "Source coding", "Invert a differential binary stream.", {}, ["in"], ["out"]),
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
    BlockSpec("python", "Python Block", "Custom", "Run a custom process(inputs, params, context) function.", {"gain": 1.0}, ["in"], ["out"], False),
]

SPEC_BY_TYPE = {spec.type: spec for spec in SPECS}


def bit_source(inputs, params, context):
    length = max(1, int(params.get("length", 4096)))
    return {"out": context.rng.integers(0, 2, length, dtype=np.int8)}


def text_source(inputs, params, context):
    text = str(params.get("text", "HELLO")) or "HELLO"
    repeat = max(1, int(params.get("repeat", 1)))
    raw = np.frombuffer(text.encode("utf-8"), dtype=np.uint8)
    bits = np.unpackbits(raw).astype(np.int8)
    stream = np.tile(bits, repeat)
    return {"out": stream, "reference": stream.copy()}


def differential_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    return {"out": np.bitwise_xor.accumulate(bits) if len(bits) else bits}


def differential_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    if not len(bits):
        return {"out": bits}
    decoded = np.empty_like(bits)
    decoded[0] = bits[0]
    if len(bits) > 1:
        decoded[1:] = np.bitwise_xor(bits[1:], bits[:-1])
    return {"out": decoded}


def hamming74_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    padding = (-len(bits)) % 4
    padded = np.pad(bits, (0, padding)) if padding else bits
    d = padded.reshape(-1, 4)
    encoded = np.empty((len(d), 7), dtype=np.int8)
    encoded[:, 2], encoded[:, 4], encoded[:, 5], encoded[:, 6] = d.T
    encoded[:, 0] = d[:, 0] ^ d[:, 1] ^ d[:, 3]
    encoded[:, 1] = d[:, 0] ^ d[:, 2] ^ d[:, 3]
    encoded[:, 3] = d[:, 1] ^ d[:, 2] ^ d[:, 3]
    return {"out": encoded.reshape(-1), "reference": bits.copy()}


def repetition3_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    return {"out": np.repeat(bits, 3), "reference": bits.copy()}


def repetition3_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    usable = bits[: len(bits) - len(bits) % 3].reshape(-1, 3)
    return {"out": (usable.sum(axis=1) >= 2).astype(np.int8)}


def bpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"])
    return {"out": 1.0 - 2.0 * bits.astype(context.xp.float32)}


def qpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"], dtype=context.xp.int8).reshape(-1)
    usable = bits[: bits.size - bits.size % 2].reshape(-1, 2)
    symbols = (1.0 - 2.0 * usable[:, 0]) + 1j * (1.0 - 2.0 * usable[:, 1])
    return {"out": symbols.astype(context.xp.complex64) / context.xp.sqrt(2.0)}


def awgn(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    # Legacy projects without snr_mode keep their fixed Eb/N0 behavior.
    mode = params.get("snr_mode", "fixed")
    ebn0_db = float(params.get("ebn0_db", 4.0)) if mode == "fixed" or context.snr_db is None else float(context.snr_db)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    if context.device == "gpu":
        noise = context.xp.random.default_rng(context.seed).normal(0.0, sigma, samples.shape)
    else:
        noise = context.rng.normal(0.0, sigma, samples.shape)
    return {"out": samples + noise}


def rayleigh(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    ebn0_db = float(params.get("ebn0_db", 4.0)) if params.get("snr_mode", "fixed") == "fixed" or context.snr_db is None else float(context.snr_db)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    if context.device == "gpu":
        random = context.xp.random.default_rng(context.seed + 17)
        fading = (random.normal(0.0, 1.0, samples.shape) + 1j * random.normal(0.0, 1.0, samples.shape)) / (2.0 ** 0.5)
        noise = random.normal(0.0, sigma, samples.shape) + 1j * random.normal(0.0, sigma, samples.shape)
    else:
        fading = (context.rng.normal(0.0, 1.0, samples.shape) + 1j * context.rng.normal(0.0, 1.0, samples.shape)) / (2.0 ** 0.5)
        noise = context.rng.normal(0.0, sigma, samples.shape) + 1j * context.rng.normal(0.0, sigma, samples.shape)
    return {"out": samples * fading + noise}


def bpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    return {"out": (samples < 0).astype(context.xp.int8)}


def qpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    bits = context.xp.empty(samples.size * 2, dtype=context.xp.int8)
    bits[0::2] = (context.xp.real(samples) < 0).astype(context.xp.int8)
    bits[1::2] = (context.xp.imag(samples) < 0).astype(context.xp.int8)
    return {"out": bits}


def hamming74_decode(inputs, params, context):
    received = to_numpy(inputs["in"]).astype(np.int8).reshape(-1)
    received = received[: len(received) - len(received) % 7].reshape(-1, 7).copy()
    if not len(received):
        return {"out": np.array([], dtype=np.int8)}
    s1 = received[:, 0] ^ received[:, 2] ^ received[:, 4] ^ received[:, 6]
    s2 = received[:, 1] ^ received[:, 2] ^ received[:, 5] ^ received[:, 6]
    s4 = received[:, 3] ^ received[:, 4] ^ received[:, 5] ^ received[:, 6]
    positions = s1 + 2 * s2 + 4 * s4
    rows = np.flatnonzero(positions)
    received[rows, positions[rows] - 1] ^= 1
    return {"out": received[:, [2, 4, 5, 6]].reshape(-1)}


def ber(inputs, params, context):
    reference = to_numpy(inputs["reference"]).astype(np.int8).reshape(-1)
    estimate = to_numpy(inputs["estimate"]).astype(np.int8).reshape(-1)
    count = min(len(reference), len(estimate))
    errors = int(np.count_nonzero(reference[:count] != estimate[:count]))
    return {"__metrics__": {"bit_errors": errors, "total_bits": count}}


def scope(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    if not len(samples):
        return {"__metrics__": {"scope_count": 0}}
    amplitude = np.abs(samples)
    return {"__metrics__": {"scope_count": int(len(samples)), "scope_sum": float(amplitude.sum()), "scope_peak": float(amplitude.max())}}


def constellation(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    if not len(samples):
        return {"__metrics__": {"constellation_count": 0}}
    return {"__metrics__": {
        "constellation_count": int(len(samples)),
        "constellation_i_sum": float(np.real(samples).sum()),
        "constellation_q_sum": float(np.imag(samples).sum()),
        "constellation_power_sum": float(np.abs(samples).sum()),
    }}


def power_meter(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    return {"__metrics__": {"power_count": int(len(samples)), "power_sum": float(np.abs(samples).astype(float).dot(np.abs(samples).astype(float))) if len(samples) else 0.0}}


def python_block(inputs, params, context, code):
    if not code:
        return {"out": inputs.get("in")}
    namespace = {"np": np, "numpy": np, "__builtins__": __builtins__}
    exec(compile(code, "<python-block>", "exec"), namespace, namespace)
    process = namespace.get("process")
    if not callable(process):
        raise ValueError("Python block must define process(inputs, params, context)")
    result = process(inputs, params, context)
    if not isinstance(result, dict):
        raise ValueError("Python block process() must return a dictionary")
    return result


PROCESSORS: dict[str, Callable] = {
    "bit_source": bit_source,
    "text_source": text_source,
    "differential_encode": differential_encode,
    "differential_decode": differential_decode,
    "hamming74_encode": hamming74_encode,
    "repetition3_encode": repetition3_encode,
    "repetition3_decode": repetition3_decode,
    "bpsk_mod": bpsk_mod,
    "qpsk_mod": qpsk_mod,
    "awgn": awgn,
    "rayleigh": rayleigh,
    "bpsk_demod": bpsk_demod,
    "qpsk_demod": qpsk_demod,
    "hamming74_decode": hamming74_decode,
    "scope": scope,
    "constellation": constellation,
    "power_meter": power_meter,
    "ber": ber,
}


def to_numpy(value):
    if isinstance(value, np.ndarray):
        return value
    if hasattr(value, "get"):
        return value.get()
    return np.asarray(value)


def make_context(xp, rng, trial_index: int, seed: int, device: str, snr_db: float | None = None):
    return SimpleNamespace(xp=xp, rng=rng, trial_index=trial_index, seed=seed, device=device, snr_db=snr_db)
