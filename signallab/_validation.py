from __future__ import annotations

from typing import Any

import numpy as np


def as_1d(value: Any, name: str = "signal", dtype: Any | None = None, allow_empty: bool = False) -> np.ndarray:
    """Convert array-like input to a validated one-dimensional NumPy array."""
    array = np.asarray(value, dtype=dtype)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional; received shape {list(array.shape)}")
    if not allow_empty and array.size == 0:
        raise ValueError(f"{name} must not be empty")
    return array


def bits(value: Any, name: str = "bits") -> np.ndarray:
    """Return a validated int8 bit vector containing only zero and one."""
    array = as_1d(value, name)
    if not np.all((array == 0) | (array == 1)):
        raise ValueError(f"{name} must contain only 0 and 1")
    return array.astype(np.int8, copy=False)


def positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    numeric = float(value)
    if not np.isfinite(numeric) or numeric < 1 or not numeric.is_integer():
        raise ValueError(f"{name} must be a positive integer")
    return int(numeric)


def probability(value: Any, name: str = "probability", inclusive: bool = True) -> float:
    numeric = float(value)
    upper_valid = numeric <= 1 if inclusive else numeric < 1
    if not np.isfinite(numeric) or numeric < 0 or not upper_valid:
        bound = "[0, 1]" if inclusive else "[0, 1)"
        raise ValueError(f"{name} must be in {bound}")
    return numeric


def random_generator(seed: int | None = -1) -> np.random.Generator:
    """Create a generator; -1/None means fresh entropy and non-negative values reproduce."""
    if seed is None or int(seed) == -1:
        return np.random.default_rng()
    numeric = int(seed)
    if numeric < 0 or numeric > 2**32 - 1:
        raise ValueError("seed must be -1, None, or an integer from 0 to 4294967295")
    return np.random.default_rng(numeric)
