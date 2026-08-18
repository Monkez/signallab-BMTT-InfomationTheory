from __future__ import annotations

import numpy as np

from ._validation import as_1d, positive_integer


def energy(signal) -> float:
    """Return discrete-time energy ``sum(|x[n]|²)``."""
    values = as_1d(signal)
    return float(np.vdot(values, values).real)


def average_power(signal) -> float:
    """Return mean discrete-time power ``mean(|x[n]|²)``."""
    values = as_1d(signal)
    return float(np.mean(np.abs(values) ** 2))


def rms(signal) -> float:
    """Return root-mean-square magnitude."""
    return float(np.sqrt(average_power(signal)))


def normalize_power(signal, target_power: float = 1.0) -> np.ndarray:
    """Scale a signal to ``target_power`` while preserving dtype complexity."""
    values = as_1d(signal)
    target = float(target_power)
    if not np.isfinite(target) or target <= 0:
        raise ValueError("target_power must be a positive finite number")
    current = average_power(values)
    if current == 0:
        raise ValueError("a zero-power signal cannot be normalized")
    return values * np.sqrt(target / current)


def db_to_linear(value_db):
    """Convert a power ratio in dB to a linear ratio."""
    return np.power(10.0, np.asarray(value_db) / 10.0)


def linear_to_db(value, floor_db: float | None = None):
    """Convert a positive linear power ratio to dB with an optional floor."""
    values = np.asarray(value, dtype=float)
    if np.any(values < 0):
        raise ValueError("linear power ratios must be non-negative")
    with np.errstate(divide="ignore"):
        result = 10.0 * np.log10(values)
    return np.maximum(result, floor_db) if floor_db is not None else result


def upsample(signal, factor: int, phase: int = 0) -> np.ndarray:
    """Insert ``factor-1`` zeros between samples."""
    values = as_1d(signal)
    rate = positive_integer(factor, "factor")
    offset = int(phase)
    if offset < 0 or offset >= rate:
        raise ValueError("phase must satisfy 0 <= phase < factor")
    output = np.zeros(values.size * rate, dtype=values.dtype)
    output[offset::rate] = values
    return output


def downsample(signal, factor: int, phase: int = 0) -> np.ndarray:
    """Keep every ``factor``-th sample beginning at ``phase``."""
    values = as_1d(signal)
    rate = positive_integer(factor, "factor")
    offset = int(phase)
    if offset < 0 or offset >= rate:
        raise ValueError("phase must satisfy 0 <= phase < factor")
    return values[offset::rate].copy()
