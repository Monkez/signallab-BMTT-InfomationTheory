from __future__ import annotations

import math
from typing import Any

import numpy as np


class SignalContractError(ValueError):
    """A block received or produced a signal with an invalid stream size."""


class BlockExecutionError(ValueError):
    """Runtime error associated with one concrete graph block."""

    def __init__(self, node_id: str, node_label: str, reason: str):
        self.node_id = node_id
        self.node_label = node_label
        self.reason = reason
        super().__init__(node_id, node_label, reason)

    def __str__(self) -> str:
        return f"Block '{self.node_label}': {self.reason}"


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise SignalContractError(f"Parameter '{name}' must be a positive integer")
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise SignalContractError(f"Parameter '{name}' must be a positive integer") from exc
    if not math.isfinite(numeric) or numeric < 1 or not numeric.is_integer():
        raise SignalContractError(f"Parameter '{name}' must be a positive integer")
    return int(numeric)


def _random_seed(value: Any) -> int:
    if isinstance(value, bool):
        raise SignalContractError("Parameter 'seed' must be -1 or an integer from 0 to 4294967295")
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise SignalContractError("Parameter 'seed' must be -1 or an integer from 0 to 4294967295") from exc
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric < -1 or numeric > 2**32 - 1:
        raise SignalContractError("Parameter 'seed' must be -1 or an integer from 0 to 4294967295")
    return int(numeric)


def validate_parameters(block_type: str, params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if block_type == "bit_source":
            _positive_integer(params.get("length", 4096), "length")
        if block_type in {"bit_source", "awgn", "rayleigh"}:
            _random_seed(params.get("seed", -1))
        if block_type in {"text_source", "text_file_source"}:
            _positive_integer(params.get("repeat", 1), "repeat")
        if block_type == "text_source" and not str(params.get("text", "HELLO")):
            raise SignalContractError("Parameter 'text' must not be empty")
        if block_type == "image_file_source" and str(params.get("mode", "grayscale")) not in {"grayscale", "rgb"}:
            raise SignalContractError("Parameter 'mode' must be 'grayscale' or 'rgb'")
        if block_type in {"huffman_encode", "huffman_decode", "shannon_fano_encode", "shannon_fano_decode"}:
            raw = str(params.get("weights", "8,4,2,1")).split(",")
            if len(raw) != 4:
                raise SignalContractError("Parameter 'weights' must contain exactly four positive integers")
            for value in raw:
                _positive_integer(value.strip(), "weights")
        if block_type in {"awgn", "rayleigh"}:
            if str(params.get("snr_mode", "fixed")) not in {"fixed", "experiment"}:
                raise SignalContractError("Parameter 'snr_mode' must be 'fixed' or 'experiment'")
            snr = float(params.get("ebn0_db", 4.0))
            if not math.isfinite(snr):
                raise SignalContractError("Parameter 'ebn0_db' must be a finite number")
        if block_type == "python":
            expected = str(params.get("output_size", "same")).strip().lower()
            if expected not in {"same", "any"}:
                _positive_integer(expected, "output_size")
    except (SignalContractError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def _signal(value: Any, port: str) -> Any:
    # NumPy and CuPy both expose ndim/size. Keep GPU arrays on-device for the
    # common shape checks; only codec-header inspection below needs host data.
    array = value if hasattr(value, "ndim") and hasattr(value, "size") else np.asarray(value)
    if array.ndim != 1:
        raise SignalContractError(f"Port '{port}' must be a 1-D signal, received shape {list(array.shape)}")
    if array.size == 0:
        raise SignalContractError(f"Port '{port}' must not be empty")
    return array


def _multiple(size: int, divisor: int, port: str, purpose: str) -> None:
    if size % divisor:
        raise SignalContractError(
            f"Port '{port}' has {size} values; {purpose} requires a multiple of {divisor}"
        )


def validate_inputs(block_type: str, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, int]:
    sizes = {name: int(_signal(value, name).size) for name, value in inputs.items()}
    primary = sizes.get("in")
    if primary is not None:
        if block_type == "hamming74_encode":
            _multiple(primary, 4, "in", "Hamming (7,4) encoding")
        elif block_type == "hamming74_decode":
            _multiple(primary, 7, "in", "Hamming (7,4) decoding")
        elif block_type == "repetition3_decode":
            _multiple(primary, 3, "in", "Repetition-3 decoding")
        elif block_type == "qpsk_mod":
            _multiple(primary, 2, "in", "QPSK modulation")
        elif block_type == "rle_decode":
            _multiple(primary, 9, "in", "Run-Length decoding")
        elif block_type in {"huffman_decode", "shannon_fano_decode", "zip_decode"} and primary < 32:
            raise SignalContractError(f"Port 'in' has {primary} values; {block_type.replace('_', ' ')} requires at least a 32-bit header")
    if block_type == "ber" and sizes.get("reference") != sizes.get("estimate"):
        raise SignalContractError(
            f"BER inputs must match exactly: reference has {sizes.get('reference', 0)} values, "
            f"estimate has {sizes.get('estimate', 0)}"
        )
    return sizes


def _encoded_original_length(block_type: str, signal: Any) -> int | None:
    bits = _signal(signal, "in")
    if hasattr(bits, "get"):
        bits = bits.get()
    bits = np.asarray(bits).astype(np.int8, copy=False)
    if block_type in {"huffman_decode", "shannon_fano_decode"}:
        return int.from_bytes(np.packbits(bits[:32]).astype(np.uint8).tobytes(), "big")
    if block_type == "zip_decode":
        return int.from_bytes(np.packbits(bits).tobytes()[:4], "big")
    if block_type == "rle_decode":
        return sum(int(np.packbits(bits[start : start + 8])[0]) for start in range(0, len(bits), 9))
    return None


def validate_outputs(
    block_type: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    declared_outputs: list[str],
    params: dict[str, Any],
) -> None:
    actual = {name for name in outputs if name != "__metrics__"}
    expected = set(declared_outputs)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise SignalContractError(f"Missing declared output port(s): {', '.join(missing)}")
    if extra:
        raise SignalContractError(f"Returned undeclared output port(s): {', '.join(extra)}")

    input_sizes = {name: int(_signal(value, name).size) for name, value in inputs.items()}
    output_sizes = {name: int(_signal(outputs[name], name).size) for name in declared_outputs}
    in_size = input_sizes.get("in")
    out_size = output_sizes.get("out")

    same_size = {
        "differential_encode", "differential_decode", "bpsk_mod", "bpsk_demod", "awgn", "rayleigh",
    }
    if block_type in same_size and out_size != in_size:
        raise SignalContractError(f"Output 'out' must match input 'in': expected {in_size}, received {out_size}")
    if block_type in {"text_source", "text_file_source", "image_file_source"} and output_sizes.get("reference") != out_size:
        raise SignalContractError("Outputs 'out' and 'reference' must have identical sizes")
    if block_type in {"huffman_encode", "shannon_fano_encode", "rle_encode", "zip_encode", "hamming74_encode", "repetition3_encode"}:
        if output_sizes.get("reference") != in_size:
            raise SignalContractError(f"Output 'reference' must match input 'in': expected {in_size}, received {output_sizes.get('reference')}")
    if block_type == "bit_source":
        expected_size = _positive_integer(params.get("length", 4096), "length")
        if out_size != expected_size:
            raise SignalContractError(f"Output 'out' must contain {expected_size} values, received {out_size}")
    if block_type == "text_source":
        expected_size = len(str(params.get("text", "HELLO")).encode("utf-8")) * 8 * _positive_integer(params.get("repeat", 1), "repeat")
        if out_size != expected_size:
            raise SignalContractError(f"Output 'out' must contain {expected_size} UTF-8 bits, received {out_size}")
    if block_type == "rle_encode" and out_size is not None:
        _multiple(out_size, 9, "out", "Run-Length encoding")
    if block_type in {"huffman_encode", "shannon_fano_encode", "zip_encode"} and (out_size or 0) < 32:
        raise SignalContractError("Encoded output must include a complete 32-bit size header")

    ratios: dict[str, tuple[int, int]] = {
        "hamming74_encode": (7, 4),
        "hamming74_decode": (4, 7),
        "repetition3_encode": (3, 1),
        "repetition3_decode": (1, 3),
        "qpsk_mod": (1, 2),
        "qpsk_demod": (2, 1),
    }
    if block_type in ratios and in_size is not None:
        numerator, denominator = ratios[block_type]
        expected_size = in_size * numerator // denominator
        if out_size != expected_size:
            raise SignalContractError(
                f"Output 'out' size mismatch: expected {expected_size} from {in_size} input values, received {out_size}"
            )

    original_length = _encoded_original_length(block_type, inputs["in"]) if block_type in {"huffman_decode", "shannon_fano_decode", "rle_decode", "zip_decode"} else None
    if original_length is not None and out_size != original_length:
        raise SignalContractError(
            f"Decoded output size mismatch: stream declares {original_length} values, decoder produced {out_size}"
        )
    if block_type == "python":
        expected = str(params.get("output_size", "same")).strip().lower()
        if expected == "same" and out_size != in_size:
            raise SignalContractError(f"Python output must match input size: expected {in_size}, received {out_size}")
        if expected not in {"same", "any"} and out_size != _positive_integer(expected, "output_size"):
            raise SignalContractError(f"Python output must contain {expected} values, received {out_size}")
