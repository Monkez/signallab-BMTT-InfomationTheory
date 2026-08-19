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


def ook_modulate(values, amplitude: float = 1.0) -> np.ndarray:
    """Map bits to on-off amplitudes ``0`` and ``amplitude``."""
    return bits(values).astype(float) * float(amplitude)


def ook_demodulate(symbols, threshold: float = 0.5) -> np.ndarray:
    """Hard-decision OOK detector; real samples at/above threshold become one."""
    values = as_1d(symbols, "symbols")
    return (np.real(values) >= float(threshold)).astype(np.int8)


def psk8_modulate(values) -> np.ndarray:
    """Gray-code groups of three bits onto eight unit-circle phases."""
    stream = bits(values)
    if stream.size % 3:
        raise ValueError(f"8-PSK requires a bit count divisible by 3; received {stream.size}")
    groups = stream.reshape(-1, 3).astype(np.int16)
    gray = (groups[:, 0] << 2) | (groups[:, 1] << 1) | groups[:, 2]
    phase_index = gray ^ (gray >> 1) ^ (gray >> 2)
    return np.exp(1j * (2.0 * np.pi / 8.0) * phase_index).astype(np.complex64)


def psk8_demodulate(symbols) -> np.ndarray:
    """Detect the nearest 8-PSK phase and return the Gray-coded input bits."""
    values = as_1d(symbols, "symbols")
    phase_index = np.rint(np.mod(np.angle(values), 2.0 * np.pi) * (8.0 / (2.0 * np.pi))).astype(np.int16) % 8
    gray = phase_index ^ (phase_index >> 1)
    output = np.empty(values.size * 3, dtype=np.int8)
    output[0::3], output[1::3], output[2::3] = (gray >> 2) & 1, (gray >> 1) & 1, gray & 1
    return output


def qam16_modulate(values, normalize: bool = True) -> np.ndarray:
    """Gray-code groups of four bits onto a square 16-QAM constellation."""
    stream = bits(values)
    if stream.size % 4:
        raise ValueError(f"16-QAM requires a bit count divisible by 4; received {stream.size}")
    groups = stream.reshape(-1, 4).astype(np.int16)
    levels = np.asarray([-3.0, -1.0, 3.0, 1.0])
    i_values = levels[(groups[:, 0] << 1) | groups[:, 1]]
    q_values = levels[(groups[:, 2] << 1) | groups[:, 3]]
    symbols = i_values + 1j * q_values
    return (symbols / np.sqrt(10.0) if normalize else symbols).astype(np.complex64)


def qam16_demodulate(symbols, normalized: bool = True) -> np.ndarray:
    """Hard-decision Gray-coded 16-QAM detector."""
    values = as_1d(symbols, "symbols")
    scaled = values * np.sqrt(10.0) if normalized else values
    i_values, q_values = np.real(scaled), np.imag(scaled)
    output = np.empty(values.size * 4, dtype=np.int8)
    output[0::4], output[1::4] = i_values > 0, np.abs(i_values) < 2.0
    output[2::4], output[3::4] = q_values > 0, np.abs(q_values) < 2.0
    return output
