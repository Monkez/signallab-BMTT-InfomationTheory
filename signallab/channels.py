from __future__ import annotations

import numpy as np

from ._validation import as_1d, bits, probability, random_generator
from .signals import average_power, db_to_linear


def awgn(signal, snr_db: float, seed: int | None = -1, measured: bool = True) -> np.ndarray:
    """Add real or complex white Gaussian noise at a requested signal-to-noise ratio."""
    values = as_1d(signal)
    signal_power = average_power(values) if measured else 1.0
    noise_power = signal_power / float(db_to_linear(float(snr_db)))
    generator = random_generator(seed)
    if np.iscomplexobj(values):
        noise = np.sqrt(noise_power / 2) * (generator.standard_normal(values.size) + 1j * generator.standard_normal(values.size))
    else:
        noise = np.sqrt(noise_power) * generator.standard_normal(values.size)
    return values + noise


def rayleigh_fading(signal, snr_db: float | None = None, seed: int | None = -1, flat: bool = False) -> np.ndarray:
    """Apply unit-power Rayleigh fading and optionally AWGN."""
    values = as_1d(signal)
    generator = random_generator(seed)
    count = 1 if flat else values.size
    coefficients = (generator.standard_normal(count) + 1j * generator.standard_normal(count)) / np.sqrt(2)
    faded = values * coefficients
    return awgn(faded, snr_db, seed=int(generator.integers(0, 2**32 - 1))) if snr_db is not None else faded


def binary_symmetric_channel(values, crossover_probability: float, seed: int | None = -1) -> np.ndarray:
    """Flip each input bit independently with probability ``p``."""
    stream = bits(values)
    p = probability(crossover_probability, "crossover_probability")
    flips = random_generator(seed).random(stream.size) < p
    return np.bitwise_xor(stream, flips.astype(np.int8))
