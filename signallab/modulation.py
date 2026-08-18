from __future__ import annotations

import numpy as np

from ._validation import as_1d, bits


def bpsk_modulate(values, amplitude: float = 1.0) -> np.ndarray:
    """Map bits ``0 → +A`` and ``1 → -A``."""
    return float(amplitude) * (1.0 - 2.0 * bits(values).astype(float))


def bpsk_demodulate(symbols, threshold: float = 0.0) -> np.ndarray:
    """Hard-decision BPSK detector; samples below threshold become one."""
    values = as_1d(symbols, "symbols")
    return (np.real(values) < float(threshold)).astype(np.int8)


def qpsk_modulate(values, normalize: bool = True) -> np.ndarray:
    """Map bit pairs to ``(+/-1) + j(+/-1)`` in input order."""
    stream = bits(values)
    if stream.size % 2:
        raise ValueError(f"QPSK requires an even bit count; received {stream.size}")
    symbols = (1 - 2 * stream[0::2]).astype(float) + 1j * (1 - 2 * stream[1::2]).astype(float)
    return symbols / np.sqrt(2) if normalize else symbols


def qpsk_demodulate(symbols) -> np.ndarray:
    """Hard-decision QPSK detector returning interleaved I/Q bits."""
    values = as_1d(symbols, "symbols")
    output = np.empty(values.size * 2, dtype=np.int8)
    output[0::2] = np.real(values) < 0
    output[1::2] = np.imag(values) < 0
    return output
