from __future__ import annotations

import math
from typing import Any

import numpy as np

from .variables import VariableDefinitionError, parse_variable_definitions
from .python_ports import PythonPortDefinitionError


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


def _validate_symbol_model(params: dict[str, Any]) -> None:
    alphabet = [token.strip() for token in str(params.get("alphabet", "A,B,C,D")).split(",")]
    if not alphabet or any(not token for token in alphabet) or len(set(alphabet)) != len(alphabet):
        raise SignalContractError("Parameter 'alphabet' must contain unique, non-empty comma-separated symbols")
    raw_probabilities = str(params.get("probabilities", "0.5,0.25,0.125,0.125")).split(",")
    if len(raw_probabilities) != len(alphabet):
        raise SignalContractError("Parameter 'probabilities' must contain one value for every alphabet symbol")
    probabilities = [float(value.strip()) for value in raw_probabilities]
    if any(not math.isfinite(value) or value <= 0 for value in probabilities):
        raise SignalContractError("Every configured probability must be a positive finite number")


def validate_parameters(block_type: str, params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if block_type == "variables":
            parse_variable_definitions(params.get("definitions", ""))
        if block_type == "bit_source":
            _positive_integer(params.get("length", 4096), "length")
        if block_type in {"bit_source", "discrete_symbol_source", "awgn", "rayleigh", "rician"}:
            _random_seed(params.get("seed", -1))
        if block_type in {"text_source", "text_file_source", "text_symbol_source", "text_file_symbol_source"}:
            _positive_integer(params.get("repeat", 1), "repeat")
        if block_type in {"text_source", "text_symbol_source"} and not str(params.get("text", "HELLO")):
            raise SignalContractError("Parameter 'text' must not be empty")
        if block_type == "discrete_symbol_source":
            _positive_integer(params.get("length", 100), "length")
        if block_type in {"discrete_symbol_source", "source_analyzer", "symbol_huffman_encode", "symbol_huffman_decode", "symbol_shannon_fano_encode", "symbol_shannon_fano_decode"}:
            _validate_symbol_model(params)
        if block_type == "image_file_source" and str(params.get("mode", "grayscale")) not in {"grayscale", "rgb"}:
            raise SignalContractError("Parameter 'mode' must be 'grayscale' or 'rgb'")
        if block_type in {"huffman_encode", "huffman_decode", "shannon_fano_encode", "shannon_fano_decode"}:
            raw = str(params.get("weights", "8,4,2,1")).split(",")
            if len(raw) != 4:
                raise SignalContractError("Parameter 'weights' must contain exactly four positive integers")
            for value in raw:
                _positive_integer(value.strip(), "weights")
        if block_type in {"awgn", "rayleigh", "rician"}:
            if str(params.get("snr_mode", "fixed")) not in {"fixed", "experiment"}:
                raise SignalContractError("Parameter 'snr_mode' must be 'fixed' or 'experiment'")
            snr = float(params.get("ebn0_db", 4.0))
            if not math.isfinite(snr):
                raise SignalContractError("Parameter 'ebn0_db' must be a finite number")
        if block_type == "rician":
            k_factor = float(params.get("k_factor_db", 6.0))
            if not math.isfinite(k_factor):
                raise SignalContractError("Parameter 'k_factor_db' must be a finite number")
        if block_type == "dc_blocker":
            alpha = float(params.get("alpha", 0.995))
            if not math.isfinite(alpha) or alpha < 0 or alpha >= 1:
                raise SignalContractError("Parameter 'alpha' must be finite and in the range [0, 1)")
        if block_type == "fir_filter":
            raw_taps = [value.strip() for value in str(params.get("taps", "0.25,0.5,0.25")).split(",")]
            if not raw_taps or any(not value for value in raw_taps):
                raise SignalContractError("Parameter 'taps' must contain comma-separated coefficients")
            taps = [float(value) for value in raw_taps]
            if any(not math.isfinite(value) for value in taps):
                raise SignalContractError("Every FIR coefficient must be finite")
        if block_type == "normalize_power":
            target_power = float(params.get("target_power", 1.0))
            if not math.isfinite(target_power) or target_power <= 0:
                raise SignalContractError("Parameter 'target_power' must be a positive finite number")
        if block_type in {"window_function", "spectrum_analyzer", "waterfall_sink"}:
            window = str(params.get("window", "hann")).strip().lower()
            if window not in {"hann", "hamming", "blackman", "rectangular"}:
                raise SignalContractError("Parameter 'window' must be hann, hamming, blackman, or rectangular")
        if block_type in {"spectrum_analyzer", "waterfall_sink"}:
            fft_size = _positive_integer(params.get("fft_size", 256 if block_type == "spectrum_analyzer" else 64), "fft_size")
            if fft_size < 8 or fft_size > 4096:
                raise SignalContractError("Parameter 'fft_size' must be an integer from 8 to 4096")
        if block_type == "python":
            expected = str(params.get("output_size", "same")).strip().lower()
            if expected not in {"same", "any"}:
                _positive_integer(expected, "output_size")
            executor = str(params.get("runtime_executor", "auto")).strip().lower()
            if executor not in {"auto", "inline", "process"}:
                raise SignalContractError("Parameter 'runtime_executor' must be 'auto', 'inline', or 'process'")
            raw_batch_size = params.get("runtime_batch_size", 0)
            if isinstance(raw_batch_size, bool):
                raise SignalContractError("Parameter 'runtime_batch_size' must be an integer from 0 to 4096")
            batch_size = float(raw_batch_size)
            if not math.isfinite(batch_size) or not batch_size.is_integer() or batch_size < 0 or batch_size > 4096:
                raise SignalContractError("Parameter 'runtime_batch_size' must be an integer from 0 to 4096")
    except (SignalContractError, VariableDefinitionError, PythonPortDefinitionError, TypeError, ValueError) as exc:
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
        elif block_type == "viterbi_decode":
            _multiple(primary, 2, "in", "Viterbi decoding")
        elif block_type == "qpsk_mod":
            _multiple(primary, 2, "in", "QPSK modulation")
        elif block_type == "psk8_mod":
            _multiple(primary, 3, "in", "8-PSK modulation")
        elif block_type == "qam16_mod":
            _multiple(primary, 4, "in", "16-QAM modulation")
        elif block_type == "rle_decode":
            _multiple(primary, 9, "in", "Run-Length decoding")
        elif block_type in {"huffman_decode", "shannon_fano_decode", "symbol_shannon_fano_decode", "zip_decode"} and primary < 32:
            raise SignalContractError(f"Port 'in' has {primary} values; {block_type.replace('_', ' ')} requires at least a 32-bit header")
        elif block_type == "symbol_huffman_decode" and bool(params.get("include_header", False)) and primary < 32:
            raise SignalContractError("Port 'in' must contain a complete 32-bit symbol-count header when include_header is enabled")
        if block_type in {"source_analyzer", "symbols_to_bits", "symbol_huffman_encode", "symbol_shannon_fano_encode"}:
            signal = _signal(inputs["in"], "in")
            if np.asarray(signal).dtype.kind not in {"U", "S", "O"}:
                raise SignalContractError(f"Port 'in' must contain text symbols, received dtype {np.asarray(signal).dtype}")
    if block_type in {"ber", "ser", "evm_meter"} and sizes.get("reference") != sizes.get("estimate"):
        raise SignalContractError(
            f"{block_type.upper()} inputs must match exactly: reference has {sizes.get('reference', 0)} values, "
            f"estimate has {sizes.get('estimate', 0)}"
        )
    return sizes


def _encoded_original_length(block_type: str, signal: Any, params: dict[str, Any]) -> int | None:
    bits = _signal(signal, "in")
    if hasattr(bits, "get"):
        bits = bits.get()
    bits = np.asarray(bits).astype(np.int8, copy=False)
    if block_type in {"huffman_decode", "shannon_fano_decode", "symbol_shannon_fano_decode"} or (block_type == "symbol_huffman_decode" and bool(params.get("include_header", False))):
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
        "differential_encode", "differential_decode", "dc_blocker", "fir_filter", "normalize_power", "window_function", "fft", "ifft", "fft_shift", "bpsk_mod", "bpsk_demod", "ook_mod", "ook_demod", "fsk2_mod", "fsk2_demod", "awgn", "rayleigh", "rician",
    }
    if block_type in same_size and out_size != in_size:
        raise SignalContractError(f"Output 'out' must match input 'in': expected {in_size}, received {out_size}")
    if block_type in {"text_source", "text_file_source", "image_file_source", "symbols_to_bits"} and output_sizes.get("reference") != out_size:
        raise SignalContractError("Outputs 'out' and 'reference' must have identical sizes")
    if block_type in {"huffman_encode", "shannon_fano_encode", "symbol_huffman_encode", "symbol_shannon_fano_encode", "rle_encode", "zip_encode", "hamming74_encode", "repetition3_encode", "convolutional_encode"}:
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
    if block_type == "text_symbol_source":
        expected_size = len(str(params.get("text", "ABACABAD"))) * _positive_integer(params.get("repeat", 1), "repeat")
        if out_size != expected_size:
            raise SignalContractError(f"Output 'out' must contain {expected_size} character symbols, received {out_size}")
    if block_type == "discrete_symbol_source":
        expected_size = _positive_integer(params.get("length", 100), "length")
        if out_size != expected_size:
            raise SignalContractError(f"Output 'out' must contain {expected_size} symbols, received {out_size}")
    if block_type == "source_analyzer" and in_size is not None:
        for port in ("symbols", "probability", "information"):
            if output_sizes.get(port) != in_size:
                raise SignalContractError(f"Output '{port}' must match input size {in_size}, received {output_sizes.get(port)}")
    if block_type == "rle_encode" and out_size is not None:
        _multiple(out_size, 9, "out", "Run-Length encoding")
    requires_header = block_type in {"huffman_encode", "shannon_fano_encode", "symbol_shannon_fano_encode", "zip_encode"} or (block_type == "symbol_huffman_encode" and bool(params.get("include_header", False)))
    if requires_header and (out_size or 0) < 32:
        raise SignalContractError("Encoded output must include a complete 32-bit size header")

    ratios: dict[str, tuple[int, int]] = {
        "hamming74_encode": (7, 4),
        "hamming74_decode": (4, 7),
        "repetition3_encode": (3, 1),
        "repetition3_decode": (1, 3),
        "convolutional_encode": (2, 1),
        "viterbi_decode": (1, 2),
        "qpsk_mod": (1, 2),
        "qpsk_demod": (2, 1),
        "psk8_mod": (1, 3),
        "psk8_demod": (3, 1),
        "qam16_mod": (1, 4),
        "qam16_demod": (4, 1),
    }
    if block_type in ratios and in_size is not None:
        numerator, denominator = ratios[block_type]
        expected_size = in_size * numerator // denominator
        if out_size != expected_size:
            raise SignalContractError(
                f"Output 'out' size mismatch: expected {expected_size} from {in_size} input values, received {out_size}"
            )

    original_length = _encoded_original_length(block_type, inputs["in"], params) if block_type in {"huffman_decode", "shannon_fano_decode", "symbol_huffman_decode", "symbol_shannon_fano_decode", "rle_decode", "zip_decode"} else None
    if original_length is not None and out_size != original_length:
        raise SignalContractError(
            f"Decoded output size mismatch: stream declares {original_length} values, decoder produced {out_size}"
        )
    if block_type == "python":
        expected = str(params.get("output_size", "same")).strip().lower()
        # Flexible PORTS declarations may have several named outputs (or no
        # signal input). In that mode each declared output is validated for
        # shape, while the legacy output_size contract remains available for
        # the default single in -> out Python Block.
        if len(declared_outputs) == 1 and declared_outputs == ["out"] and len(inputs) == 1 and "in" in inputs and expected == "same" and out_size != in_size:
            raise SignalContractError(f"Python output must match input size: expected {in_size}, received {out_size}")
        if len(declared_outputs) == 1 and declared_outputs == ["out"] and len(inputs) == 1 and "in" in inputs and expected not in {"same", "any"} and out_size != _positive_integer(expected, "output_size"):
            raise SignalContractError(f"Python output must contain {expected} values, received {out_size}")
