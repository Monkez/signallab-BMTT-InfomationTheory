from __future__ import annotations

import numpy as np

from ._validation import as_1d, bits
from .signals import average_power, linear_to_db


def bit_errors(reference, estimate) -> int:
    """Count unequal bits; lengths must match exactly."""
    expected, actual = bits(reference, "reference"), bits(estimate, "estimate")
    if expected.size != actual.size:
        raise ValueError(f"bit vectors must match exactly: {expected.size} != {actual.size}")
    return int(np.count_nonzero(expected != actual))


def ber(reference, estimate) -> float:
    """Return bit-error rate as errors divided by compared bits."""
    expected = bits(reference, "reference")
    return bit_errors(expected, estimate) / expected.size


def symbol_errors(reference, estimate) -> int:
    """Count unequal arbitrary symbols with exact-size checking."""
    expected, actual = as_1d(reference, "reference"), as_1d(estimate, "estimate")
    if expected.size != actual.size:
        raise ValueError(f"symbol vectors must match exactly: {expected.size} != {actual.size}")
    return int(np.count_nonzero(expected != actual))


def ser(reference, estimate) -> float:
    """Return symbol-error rate."""
    expected = as_1d(reference, "reference")
    return symbol_errors(expected, estimate) / expected.size


def evm_rms(reference, estimate, percent: bool = True) -> float:
    """Return RMS error-vector magnitude normalized by reference RMS."""
    expected, actual = as_1d(reference, "reference"), as_1d(estimate, "estimate")
    if expected.size != actual.size:
        raise ValueError(f"vectors must match exactly: {expected.size} != {actual.size}")
    value = np.sqrt(average_power(actual - expected) / average_power(expected))
    return float(value * 100 if percent else value)


def measured_snr_db(clean, noisy) -> float:
    """Estimate SNR from a known clean reference and noisy observation."""
    reference, observation = as_1d(clean, "clean"), as_1d(noisy, "noisy")
    if reference.size != observation.size:
        raise ValueError(f"vectors must match exactly: {reference.size} != {observation.size}")
    return float(linear_to_db(average_power(reference) / average_power(observation - reference)))
