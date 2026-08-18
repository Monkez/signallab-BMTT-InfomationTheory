from __future__ import annotations

import numpy as np

from ._validation import bits, positive_integer


def repetition_encode(values, repeat: int = 3) -> np.ndarray:
    """Repeat every bit ``repeat`` times."""
    return np.repeat(bits(values), positive_integer(repeat, "repeat"))


def repetition_decode(values, repeat: int = 3) -> np.ndarray:
    """Majority-decode fixed-size repetition groups."""
    stream = bits(values)
    count = positive_integer(repeat, "repeat")
    if stream.size % count:
        raise ValueError(f"input length must be divisible by repeat={count}; received {stream.size}")
    return (stream.reshape(-1, count).sum(axis=1) > count / 2).astype(np.int8)


def hamming74_encode(values) -> np.ndarray:
    """Encode systematic Hamming words as ``[d1,d2,d3,d4,p1,p2,p3]``."""
    stream = bits(values)
    if stream.size % 4:
        raise ValueError(f"Hamming (7,4) input length must be divisible by 4; received {stream.size}")
    data = stream.reshape(-1, 4)
    output = np.empty((len(data), 7), dtype=np.int8)
    output[:, :4] = data
    output[:, 4] = data[:, 0] ^ data[:, 1] ^ data[:, 3]
    output[:, 5] = data[:, 0] ^ data[:, 2] ^ data[:, 3]
    output[:, 6] = data[:, 1] ^ data[:, 2] ^ data[:, 3]
    return output.reshape(-1)


def hamming74_decode(values) -> np.ndarray:
    """Correct one error per systematic Hamming word and return data bits."""
    stream = bits(values)
    if stream.size % 7:
        raise ValueError(f"Hamming (7,4) input length must be divisible by 7; received {stream.size}")
    received = stream.reshape(-1, 7).copy()
    syndrome = (received[:, 0] ^ received[:, 1] ^ received[:, 3] ^ received[:, 4])
    syndrome += 2 * (received[:, 0] ^ received[:, 2] ^ received[:, 3] ^ received[:, 5])
    syndrome += 4 * (received[:, 1] ^ received[:, 2] ^ received[:, 3] ^ received[:, 6])
    error_indices = np.array([-1, 4, 5, 0, 6, 1, 2, 3], dtype=np.int8)
    rows = np.flatnonzero(syndrome)
    received[rows, error_indices[syndrome[rows]]] ^= 1
    return received[:, :4].reshape(-1)
