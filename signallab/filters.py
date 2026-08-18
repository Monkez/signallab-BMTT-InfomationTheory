from __future__ import annotations

import numpy as np
from scipy import signal as scipy_signal

from ._validation import as_1d, positive_integer


def fir_lowpass(cutoff_hz: float, sample_rate_hz: float, num_taps: int = 101, window: str = "hamming") -> np.ndarray:
    """Design a linear-phase low-pass FIR filter using ``scipy.signal.firwin``."""
    cutoff, sample_rate = float(cutoff_hz), float(sample_rate_hz)
    if not 0 < cutoff < sample_rate / 2:
        raise ValueError("cutoff_hz must be between 0 and the Nyquist frequency")
    return scipy_signal.firwin(positive_integer(num_taps, "num_taps"), cutoff, fs=sample_rate, window=window)


def fir_bandpass(low_hz: float, high_hz: float, sample_rate_hz: float, num_taps: int = 101, window: str = "hamming") -> np.ndarray:
    """Design a linear-phase band-pass FIR filter."""
    low, high, sample_rate = float(low_hz), float(high_hz), float(sample_rate_hz)
    if not 0 < low < high < sample_rate / 2:
        raise ValueError("require 0 < low_hz < high_hz < sample_rate_hz/2")
    return scipy_signal.firwin(positive_integer(num_taps, "num_taps"), [low, high], pass_zero=False, fs=sample_rate, window=window)


def apply_fir(signal, taps, mode: str = "same") -> np.ndarray:
    """Convolve a signal with FIR taps using SciPy's FFT convolution."""
    values, coefficients = as_1d(signal), as_1d(taps, "taps")
    if mode not in {"full", "same", "valid"}:
        raise ValueError("mode must be 'full', 'same', or 'valid'")
    return scipy_signal.fftconvolve(values, coefficients, mode=mode)


def matched_filter(signal, pulse, mode: str = "same") -> np.ndarray:
    """Apply the matched filter ``conj(pulse[::-1])``."""
    template = as_1d(pulse, "pulse")
    return apply_fir(signal, np.conjugate(template[::-1]), mode=mode)


def root_raised_cosine(beta: float, samples_per_symbol: int, span_symbols: int = 8) -> np.ndarray:
    """Return unit-energy root-raised-cosine taps sampled symmetrically."""
    rolloff = float(beta)
    if not 0 <= rolloff <= 1:
        raise ValueError("beta must be in [0, 1]")
    sps = positive_integer(samples_per_symbol, "samples_per_symbol")
    span = positive_integer(span_symbols, "span_symbols")
    t = np.arange(-span * sps / 2, span * sps / 2 + 1) / sps
    taps = np.empty_like(t, dtype=float)
    for index, value in enumerate(t):
        if abs(value) < 1e-12:
            taps[index] = 1 + rolloff * (4 / np.pi - 1)
        elif rolloff > 0 and abs(abs(value) - 1 / (4 * rolloff)) < 1e-10:
            taps[index] = rolloff / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * rolloff)) + (1 - 2 / np.pi) * np.cos(np.pi / (4 * rolloff)))
        else:
            numerator = np.sin(np.pi * value * (1 - rolloff)) + 4 * rolloff * value * np.cos(np.pi * value * (1 + rolloff))
            denominator = np.pi * value * (1 - (4 * rolloff * value) ** 2)
            taps[index] = numerator / denominator
    return taps / np.sqrt(np.sum(taps**2))
