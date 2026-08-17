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
    BlockSpec("hamming74_encode", "Hamming (7,4) Encoder", "Channel coding", "Encode 4 data bits into a Hamming(7,4) codeword.", {}, ["in"], ["out", "reference"]),
    BlockSpec("bpsk_mod", "BPSK Modulator", "Modulation", "Map 0 → +1 and 1 → -1.", {}, ["in"], ["out"]),
    BlockSpec("awgn", "AWGN Channel", "Channels", "Add white Gaussian noise for the configured Eb/N0.", {"ebn0_db": 4.0}, ["in"], ["out"]),
    BlockSpec("bpsk_demod", "BPSK Demodulator", "Receivers", "Hard-decision BPSK detector.", {}, ["in"], ["out"]),
    BlockSpec("hamming74_decode", "Hamming (7,4) Decoder", "Channel coding", "Syndrome decode and correct one bit per codeword.", {}, ["in"], ["out"]),
    BlockSpec("ber", "BER Meter", "Sinks", "Compare received bits with a reference stream.", {}, ["reference", "estimate"], []),
    BlockSpec("python", "Python Block", "Custom", "Run a custom process(inputs, params, context) function.", {"gain": 1.0}, ["in"], ["out"], False),
]

SPEC_BY_TYPE = {spec.type: spec for spec in SPECS}


def bit_source(inputs, params, context):
    length = max(1, int(params.get("length", 4096)))
    return {"out": context.rng.integers(0, 2, length, dtype=np.int8)}


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


def bpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"])
    return {"out": 1.0 - 2.0 * bits.astype(context.xp.float32)}


def awgn(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    ebn0_db = float(params.get("ebn0_db", 4.0))
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    if context.device == "gpu":
        noise = context.xp.random.default_rng(context.seed).normal(0.0, sigma, samples.shape)
    else:
        noise = context.rng.normal(0.0, sigma, samples.shape)
    return {"out": samples + noise}


def bpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    return {"out": (samples < 0).astype(context.xp.int8)}


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
    "hamming74_encode": hamming74_encode,
    "bpsk_mod": bpsk_mod,
    "awgn": awgn,
    "bpsk_demod": bpsk_demod,
    "hamming74_decode": hamming74_decode,
    "ber": ber,
}


def to_numpy(value):
    if isinstance(value, np.ndarray):
        return value
    if hasattr(value, "get"):
        return value.get()
    return np.asarray(value)


def make_context(xp, rng, trial_index: int, seed: int, device: str):
    return SimpleNamespace(xp=xp, rng=rng, trial_index=trial_index, seed=seed, device=device)

