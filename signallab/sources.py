from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ._validation import positive_integer, random_generator


def random_bits(length: int, seed: int | None = -1) -> np.ndarray:
    """Generate ``length`` equiprobable bits as an ``int8`` vector."""
    size = positive_integer(length, "length")
    return random_generator(seed).integers(0, 2, size=size, dtype=np.int8)


def random_symbols(
    alphabet: Sequence[str], probabilities: Sequence[float], length: int, seed: int | None = -1
) -> np.ndarray:
    """Draw symbols from a discrete memoryless source with normalized weights."""
    symbols = [str(item) for item in alphabet]
    if not symbols or any(not item for item in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("alphabet must contain unique, non-empty symbols")
    weights = np.asarray(probabilities, dtype=float)
    if weights.ndim != 1 or len(weights) != len(symbols) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("probabilities must contain one positive finite value per symbol")
    weights /= weights.sum()
    indices = random_generator(seed).choice(len(symbols), size=positive_integer(length, "length"), p=weights)
    width = max(len(item) for item in symbols)
    return np.asarray(symbols, dtype=f"<U{width}")[indices]


def text_symbols(text: str, repeat: int = 1) -> np.ndarray:
    """Split Unicode text into visible character symbols."""
    if not text:
        raise ValueError("text must not be empty")
    return np.tile(np.asarray(list(str(text)), dtype="<U1"), positive_integer(repeat, "repeat"))


def text_to_bits(text: str, encoding: str = "utf-8") -> np.ndarray:
    """Encode text to a big-endian-per-byte bit vector."""
    raw = str(text).encode(encoding)
    if not raw:
        raise ValueError("text must not be empty")
    return np.unpackbits(np.frombuffer(raw, dtype=np.uint8)).astype(np.int8)


def bits_to_text(values, encoding: str = "utf-8", errors: str = "strict") -> str:
    """Pack a byte-aligned bit vector and decode it as text."""
    from ._validation import bits

    stream = bits(values)
    if stream.size % 8:
        raise ValueError(f"bit length must be divisible by 8; received {stream.size}")
    return np.packbits(stream).tobytes().decode(encoding, errors=errors)
