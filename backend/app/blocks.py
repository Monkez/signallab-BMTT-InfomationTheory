from __future__ import annotations

import ast
import base64
import copy
import heapq
import inspect
import math
import secrets
import traceback
import zlib
from functools import lru_cache
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np
import scipy as sp

import signallab as sl

from .python_ports import parse_python_ports


def _block_rng(params, context, backend=np, salt: int = 0):
    configured_seed = int(params.get("seed", -1))
    base_seed = context.random_seed_root if configured_seed == -1 else configured_seed
    node_hash = zlib.crc32(str(getattr(context, "node_id", "")).encode("utf-8"))
    entropy = [
        int(base_seed) & 0xFFFFFFFF,
        (int(base_seed) >> 32) & 0xFFFFFFFF,
        int(context.seed) & 0xFFFFFFFF,
        node_hash,
        int(salt) & 0xFFFFFFFF,
    ]
    derived_seed = int(np.random.SeedSequence(entropy).generate_state(1, dtype=np.uint32)[0])
    return backend.random.default_rng(derived_seed)


def bit_source(inputs, params, context):
    length = max(1, int(params.get("length", 4096)))
    return {"out": _block_rng(params, context).integers(0, 2, length, dtype=np.int8)}


def text_source(inputs, params, context):
    text = str(params.get("text", "HELLO")) or "HELLO"
    repeat = max(1, int(params.get("repeat", 1)))
    raw = np.frombuffer(text.encode("utf-8"), dtype=np.uint8)
    bits = np.unpackbits(raw).astype(np.int8)
    stream = np.tile(bits, repeat)
    return {"out": stream, "reference": stream.copy()}


def _symbol_array(values):
    items = [str(value) for value in values]
    width = max((len(value) for value in items), default=1)
    return np.asarray(items, dtype=f"<U{max(1, width)}")


def _symbol_model(params):
    aliases = {"<space>": " ", r"\n": "\n", r"\t": "\t"}
    alphabet = [aliases.get(token.strip(), token.strip()) for token in str(params.get("alphabet", "A,B,C,D")).split(",")]
    if not alphabet or any(not symbol for symbol in alphabet) or len(set(alphabet)) != len(alphabet):
        raise ValueError("alphabet must contain unique, non-empty comma-separated symbols")
    try:
        probabilities = np.asarray([float(value.strip()) for value in str(params.get("probabilities", "0.5,0.25,0.125,0.125")).split(",")], dtype=float)
    except ValueError as exc:
        raise ValueError("probabilities must be comma-separated positive numbers") from exc
    if len(probabilities) != len(alphabet) or not np.all(np.isfinite(probabilities)) or np.any(probabilities <= 0):
        raise ValueError("probabilities must contain one positive value for every alphabet symbol")
    probabilities /= probabilities.sum()
    return alphabet, probabilities


def text_symbol_source(inputs, params, context):
    text = str(params.get("text", "ABACABAD"))
    repeat = max(1, int(params.get("repeat", 1)))
    return {"out": np.tile(_symbol_array(text), repeat)}


def text_file_symbol_source(inputs, params, context):
    try:
        text = _file_bytes(params).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("The selected text file is not valid UTF-8") from exc
    repeat = max(1, int(params.get("repeat", 1)))
    return {"out": np.tile(_symbol_array(text), repeat)}


def discrete_symbol_source(inputs, params, context):
    alphabet, probabilities = _symbol_model(params)
    length = max(1, int(params.get("length", 100)))
    indices = _block_rng(params, context).choice(len(alphabet), size=length, p=probabilities)
    return {"out": _symbol_array(alphabet)[indices]}


def source_analyzer(inputs, params, context):
    symbols = _symbol_array(np.asarray(inputs["in"]).reshape(-1))
    alphabet, probabilities = _symbol_model(params)
    lookup = {symbol: index for index, symbol in enumerate(alphabet)}
    unknown = sorted({str(symbol) for symbol in symbols if str(symbol) not in lookup})
    if unknown:
        raise ValueError(f"input contains symbols outside alphabet: {', '.join(repr(value) for value in unknown[:5])}")
    indices = np.asarray([lookup[str(symbol)] for symbol in symbols], dtype=np.int64)
    per_symbol_probability = probabilities[indices]
    information = -np.log2(per_symbol_probability)
    entropy = float(-(probabilities * np.log2(probabilities)).sum())
    max_entropy = float(np.log2(len(alphabet))) if len(alphabet) > 1 else 0.0
    efficiency = 100.0 * entropy / max_entropy if max_entropy else 100.0
    return {
        "symbols": symbols.copy(),
        "probability": per_symbol_probability,
        "information": information,
        "__metrics__": {
            "source_frame_count": 1,
            "source_symbol_count": len(symbols),
            "source_information_sum": float(information.sum()),
            "source_entropy_sum": entropy,
            "source_max_entropy_sum": max_entropy,
            "source_efficiency_sum": efficiency,
            "source_alphabet_size_peak": len(alphabet),
        },
    }


def symbols_to_bits(inputs, params, context):
    symbols = np.asarray(inputs["in"]).astype(str).reshape(-1)
    separator = str(params.get("separator", ""))
    raw = separator.join(symbols.tolist()).encode("utf-8")
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8)).astype(np.int8)
    return {"out": bits, "reference": bits.copy()}


def _file_bytes(params):
    encoded = str(params.get("data_base64", ""))
    if not encoded:
        raise ValueError("Select a file before running this source block")
    try:
        return base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("The selected file data is not valid base64") from exc


def text_file_source(inputs, params, context):
    raw = _file_bytes(params)
    repeat = max(1, int(params.get("repeat", 1)))
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8)).astype(np.int8)
    stream = np.tile(bits, repeat)
    return {"out": stream, "reference": stream.copy()}


def image_file_source(inputs, params, context):
    raw = _file_bytes(params)
    try:
        from PIL import Image
        image = Image.open(BytesIO(raw)).convert("L" if str(params.get("mode", "grayscale")) == "grayscale" else "RGB")
        pixels = np.asarray(image, dtype=np.uint8).reshape(-1)
    except Exception as exc:
        raise ValueError("The selected file is not a readable image") from exc
    bits = np.unpackbits(pixels).astype(np.int8)
    return {"out": bits, "reference": bits.copy()}


def _weights(params):
    try:
        values = [max(1, int(value.strip())) for value in str(params.get("weights", "8,4,2,1")).split(",")]
    except ValueError as exc:
        raise ValueError("weights must be comma-separated positive integers") from exc
    return (values + [1, 1, 1, 1])[:4]


def _huffman_codes(weights):
    heap = [[weight, [symbol, ""]] for symbol, weight in enumerate(weights)]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        for item in left[1:]: item[1] = "0" + item[1]
        for item in right[1:]: item[1] = "1" + item[1]
        heapq.heappush(heap, [left[0] + right[0], *left[1:], *right[1:]])
    return {symbol: code or "0" for symbol, code in heap[0][1:]}


def _stable_huffman_codes(weights):
    """Deterministic teaching codebook: equal weights keep insertion order."""
    queue = [
        {"weight": float(weight), "order": symbol, "codes": {symbol: ""}}
        for symbol, weight in enumerate(weights)
    ]
    next_order = len(queue)
    while len(queue) > 1:
        queue.sort(key=lambda item: (item["weight"], item["order"]))
        left, right = queue.pop(0), queue.pop(0)
        codes = {
            **{symbol: "0" + code for symbol, code in left["codes"].items()},
            **{symbol: "1" + code for symbol, code in right["codes"].items()},
        }
        queue.append({"weight": left["weight"] + right["weight"], "order": next_order, "codes": codes})
        next_order += 1
    return {symbol: code or "0" for symbol, code in queue[0]["codes"].items()}


def _shannon_fano_codes(weights):
    codes = {symbol: "" for symbol in range(4)}
    ordered = sorted(enumerate(weights), key=lambda item: (-item[1], item[0]))

    def split(items):
        if len(items) <= 1:
            return
        total = sum(weight for _, weight in items)
        running = 0
        cut = 1
        for index, (_, weight) in enumerate(items[:-1], 1):
            running += weight
            if abs(total / 2 - running) < abs(total / 2 - sum(value for _, value in items[:cut])):
                cut = index
        for symbol, _ in items[:cut]: codes[symbol] += "0"
        for symbol, _ in items[cut:]: codes[symbol] += "1"
        split(items[:cut]); split(items[cut:])

    split(ordered)
    return {symbol: code or "0" for symbol, code in codes.items()}


def _pack_symbol_bits(bits):
    values = np.asarray(bits, dtype=np.int8).reshape(-1)
    padding = (-len(values)) % 2
    padded = np.pad(values, (0, padding)) if padding else values
    return (padded[0::2] * 2 + padded[1::2]).astype(np.int8), len(values)


def _variable_encode(inputs, params, code_factory):
    symbols, original_length = _pack_symbol_bits(inputs["in"])
    codes = code_factory(_weights(params))
    encoded = [int(bit) for symbol in symbols for bit in codes[int(symbol)]]
    header = np.unpackbits(np.array([original_length], dtype=">u4").view(np.uint8)).astype(np.int8)
    return {"out": np.concatenate([header, np.asarray(encoded, dtype=np.int8)]), "reference": np.asarray(inputs["in"], dtype=np.int8).copy()}


def _variable_decode(inputs, params, code_factory):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    if len(bits) < 32:
        return {"out": np.array([], dtype=np.int8)}
    header = np.packbits(bits[:32]).astype(np.uint8)
    original_length = int.from_bytes(header.tobytes(), "big")
    codes = code_factory(_weights(params))
    reverse = {code: symbol for symbol, code in codes.items()}
    decoded = []
    token = ""
    for bit in bits[32:]:
        token += str(int(bit))
        if token in reverse:
            symbol = reverse[token]
            decoded.extend([symbol // 2, symbol % 2])
            token = ""
    return {"out": np.asarray(decoded[:original_length], dtype=np.int8)}


def huffman_encode(inputs, params, context): return _variable_encode(inputs, params, _huffman_codes)
def huffman_decode(inputs, params, context): return _variable_decode(inputs, params, _huffman_codes)
def shannon_fano_encode(inputs, params, context): return _variable_encode(inputs, params, _shannon_fano_codes)
def shannon_fano_decode(inputs, params, context): return _variable_decode(inputs, params, _shannon_fano_codes)


def _symbol_variable_encode(inputs, params, code_factory):
    symbols = np.asarray(inputs["in"]).astype(str).reshape(-1)
    alphabet, probabilities = _symbol_model(params)
    lookup = {symbol: index for index, symbol in enumerate(alphabet)}
    unknown = sorted({str(symbol) for symbol in symbols if str(symbol) not in lookup})
    if unknown:
        raise ValueError(f"input contains symbols outside alphabet: {', '.join(repr(value) for value in unknown[:5])}")
    codes = code_factory(probabilities.tolist())
    encoded = [int(bit) for symbol in symbols for bit in codes[lookup[str(symbol)]]]
    payload = np.asarray(encoded, dtype=np.int8)
    if bool(params.get("include_header", False)):
        header = np.unpackbits(np.array([len(symbols)], dtype=">u4").view(np.uint8)).astype(np.int8)
        payload = np.concatenate([header, payload])
    return {"out": payload, "reference": _symbol_array(symbols)}


def _symbol_variable_decode(inputs, params, code_factory):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    include_header = bool(params.get("include_header", False))
    original_length = int.from_bytes(np.packbits(bits[:32]).astype(np.uint8).tobytes(), "big") if include_header else None
    payload = bits[32:] if include_header else bits
    alphabet, probabilities = _symbol_model(params)
    reverse = {code: alphabet[index] for index, code in code_factory(probabilities.tolist()).items()}
    decoded = []
    token = ""
    for bit in payload:
        token += str(int(bit))
        if token in reverse:
            decoded.append(reverse[token])
            token = ""
    if token:
        raise ValueError(f"encoded payload ends with incomplete codeword {token!r}")
    if original_length is not None and len(decoded) != original_length:
        raise ValueError(f"header declares {original_length} symbols but payload decodes to {len(decoded)}")
    return {"out": _symbol_array(decoded)}


def symbol_huffman_encode(inputs, params, context): return _symbol_variable_encode(inputs, params, _stable_huffman_codes)
def symbol_huffman_decode(inputs, params, context): return _symbol_variable_decode(inputs, params, _stable_huffman_codes)
def symbol_shannon_fano_encode(inputs, params, context): return _symbol_variable_encode(inputs, params, _shannon_fano_codes)
def symbol_shannon_fano_decode(inputs, params, context): return _symbol_variable_decode(inputs, params, _shannon_fano_codes)


def rle_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    encoded = []
    index = 0
    while index < len(bits):
        value = int(bits[index]); end = index + 1
        while end < len(bits) and int(bits[end]) == value and end - index < 255: end += 1
        encoded.extend(np.unpackbits(np.array([end - index], dtype=np.uint8)).tolist())
        encoded.append(value); index = end
    return {"out": np.asarray(encoded, dtype=np.int8), "reference": bits.copy()}


def rle_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    decoded = []
    for start in range(0, len(bits) - 8, 9):
        count = int(np.packbits(bits[start:start + 8])[0])
        decoded.extend([int(bits[start + 8])] * count)
    return {"out": np.asarray(decoded, dtype=np.int8)}


def zip_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    packed = np.packbits(bits)
    payload = zlib.compress(packed.tobytes())
    header = len(bits).to_bytes(4, "big")
    return {"out": np.unpackbits(np.frombuffer(header + payload, dtype=np.uint8)).astype(np.int8), "reference": bits.copy()}


def zip_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    raw = np.packbits(bits).tobytes()
    if len(raw) < 4:
        return {"out": np.array([], dtype=np.int8)}
    try:
        length = int.from_bytes(raw[:4], "big")
        unpacked = np.unpackbits(np.frombuffer(zlib.decompress(raw[4:]), dtype=np.uint8)).astype(np.int8)
    except zlib.error as exc:
        raise ValueError("ZIP decoder received an invalid compressed stream") from exc
    return {"out": unpacked[:length]}


def differential_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    return {"out": np.bitwise_xor.accumulate(bits) if len(bits) else bits}


def differential_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    if not len(bits):
        return {"out": bits}
    decoded = np.empty_like(bits)
    decoded[0] = bits[0]
    if len(bits) > 1:
        decoded[1:] = np.bitwise_xor(bits[1:], bits[:-1])
    return {"out": decoded}


def convolutional_encode(inputs, params, context):
    """Rate-1/2, constraint-length-3 encoder with octal generators (7, 5)."""
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    encoded = np.empty(bits.size * 2, dtype=np.int8)
    previous_1 = 0
    previous_2 = 0
    for index, bit_value in enumerate(bits):
        bit = int(bit_value) & 1
        encoded[2 * index] = bit ^ previous_1 ^ previous_2
        encoded[2 * index + 1] = bit ^ previous_2
        previous_2 = previous_1
        previous_1 = bit
    return {"out": encoded, "reference": bits.copy()}


def viterbi_decode(inputs, params, context):
    """Hard-decision Viterbi decoder matched to the (7, 5) encoder."""
    received = np.asarray(inputs["in"], dtype=np.int8).reshape(-1, 2)
    state_count = 4
    infinity = np.iinfo(np.int32).max // 4
    metrics = np.full(state_count, infinity, dtype=np.int32)
    metrics[0] = 0
    predecessor = np.empty((len(received), state_count), dtype=np.int8)
    decisions = np.empty((len(received), state_count), dtype=np.int8)
    for time_index, pair in enumerate(received):
        next_metrics = np.full(state_count, infinity, dtype=np.int32)
        for state in range(state_count):
            if metrics[state] >= infinity:
                continue
            previous_1 = (state >> 1) & 1
            previous_2 = state & 1
            for bit in (0, 1):
                expected_0 = bit ^ previous_1 ^ previous_2
                expected_1 = bit ^ previous_2
                distance = int(pair[0] != expected_0) + int(pair[1] != expected_1)
                next_state = (bit << 1) | previous_1
                candidate = int(metrics[state]) + distance
                if candidate < next_metrics[next_state]:
                    next_metrics[next_state] = candidate
                    predecessor[time_index, next_state] = state
                    decisions[time_index, next_state] = bit
        metrics = next_metrics
    state = int(np.argmin(metrics))
    decoded = np.empty(len(received), dtype=np.int8)
    for time_index in range(len(received) - 1, -1, -1):
        decoded[time_index] = decisions[time_index, state]
        state = int(predecessor[time_index, state])
    return {"out": decoded}


def hamming74_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    d = bits.reshape(-1, 4)
    encoded = np.empty((len(d), 7), dtype=np.int8)
    # Systematic Hamming (7,4): [d1, d2, d3, d4, p1, p2, p3].
    encoded[:, :4] = d
    encoded[:, 4] = d[:, 0] ^ d[:, 1] ^ d[:, 3]
    encoded[:, 5] = d[:, 0] ^ d[:, 2] ^ d[:, 3]
    encoded[:, 6] = d[:, 1] ^ d[:, 2] ^ d[:, 3]
    return {"out": encoded.reshape(-1), "reference": bits.copy()}


def _parse_polynomial(value, default: int) -> int:
    text = str(value if value is not None else default).strip().lower()
    return int(text, 0)


def _poly_remainder(bits: np.ndarray, generator: int, degree: int) -> np.ndarray:
    work = bits.astype(np.int8, copy=True)
    taps = np.array([(generator >> (degree - index)) & 1 for index in range(degree + 1)], dtype=np.int8)
    for index in range(max(0, work.size - degree)):
        if work[index]:
            work[index:index + degree + 1] ^= taps
    return work[-degree:] if degree else np.empty(0, dtype=np.int8)


def cyclic_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1
    generator = _parse_polynomial(params.get("generator", "0b10011"), 0b10011)
    degree = max(1, generator.bit_length() - 1)
    parity = _poly_remainder(np.concatenate([bits, np.zeros(degree, dtype=np.int8)]), generator, degree)
    return {"out": np.concatenate([bits, parity]), "reference": bits.copy()}


def cyclic_decode(inputs, params, context):
    received = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1
    generator = _parse_polynomial(params.get("generator", "0b10011"), 0b10011)
    degree = max(1, generator.bit_length() - 1)
    if received.size <= degree:
        raise ValueError("Cyclic codeword must contain data bits plus generator parity")
    if bool(params.get("check", False)) and np.any(_poly_remainder(received, generator, degree)):
        raise ValueError("Cyclic decoder detected a non-zero syndrome")
    return {"out": received[:-degree]}


def _bch_codewords() -> np.ndarray:
    generator = 0b101110001  # primitive binary BCH(15,7), t=2 generator
    words = np.empty((128, 15), dtype=np.int8)
    for value in range(128):
        data = np.array([(value >> (6 - index)) & 1 for index in range(7)], dtype=np.int8)
        parity = _poly_remainder(np.concatenate([data, np.zeros(8, dtype=np.int8)]), generator, 8)
        words[value] = np.concatenate([data, parity])
    return words


def bch_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1
    if bits.size % 7:
        raise ValueError("BCH(15,7) encoding requires a multiple of 7 input bits")
    words = _bch_codewords(); values = bits.reshape(-1, 7).dot(1 << np.arange(6, -1, -1))
    return {"out": words[values].reshape(-1), "reference": bits.copy()}


def bch_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1
    if bits.size % 15:
        raise ValueError("BCH(15,7) decoding requires a multiple of 15 input bits")
    words = _bch_codewords(); received = bits.reshape(-1, 15)
    decoded = []
    for word in received:
        distances = np.count_nonzero(words ^ word, axis=1)
        decoded.append(words[int(np.argmin(distances)), :7])
    return {"out": np.asarray(decoded, dtype=np.int8).reshape(-1)}


def _gf_tables():
    exp = np.zeros(512, dtype=np.uint8); log = np.full(256, -1, dtype=np.int16); value = 1
    for index in range(255):
        exp[index] = value; log[value] = index; value <<= 1
        if value & 0x100: value ^= 0x11D
    for index in range(255, 512): exp[index] = exp[index - 255]
    return exp, log


def _gf_mul(a: int, b: int, exp: np.ndarray, log: np.ndarray) -> int:
    return 0 if not a or not b else int(exp[int(log[a]) + int(log[b])])


def _rs_generator(parity: int, exp: np.ndarray, log: np.ndarray) -> list[int]:
    generator = [1]
    for root in range(parity):
        factor = int(exp[root]); next_poly = [0] * (len(generator) + 1)
        for index, coefficient in enumerate(generator):
            next_poly[index] ^= coefficient
            next_poly[index + 1] ^= _gf_mul(coefficient, factor, exp, log)
        generator = next_poly
    return generator


def _rs_parity(data: np.ndarray, parity: int) -> np.ndarray:
    exp, log = _gf_tables(); generator = _rs_generator(parity, exp, log); remainder = [0] * parity
    for byte in data:
        feedback = int(byte) ^ remainder[0]
        remainder = remainder[1:] + [0]
        for index in range(parity): remainder[index] ^= _gf_mul(feedback, generator[index + 1], exp, log)
    return np.asarray(remainder, dtype=np.uint8)


def reed_solomon_encode(inputs, params, context):
    symbols = np.asarray(inputs["in"], dtype=np.uint8).reshape(-1); data_symbols = max(1, int(params.get("data_symbols", 11))); parity_symbols = max(1, int(params.get("parity_symbols", 4)))
    if symbols.size % data_symbols: raise ValueError(f"Reed-Solomon encoding requires a multiple of {data_symbols} byte symbols")
    blocks = [np.concatenate([block, _rs_parity(block, parity_symbols)]) for block in symbols.reshape(-1, data_symbols)]
    return {"out": np.concatenate(blocks).astype(np.uint8), "reference": symbols.copy()}


def reed_solomon_decode(inputs, params, context):
    symbols = np.asarray(inputs["in"], dtype=np.uint8).reshape(-1); data_symbols = max(1, int(params.get("data_symbols", 11))); parity_symbols = max(1, int(params.get("parity_symbols", 4))); codeword = data_symbols + parity_symbols
    if symbols.size % codeword: raise ValueError(f"Reed-Solomon decoding requires a multiple of {codeword} symbols")
    decoded = []
    for block in symbols.reshape(-1, codeword):
        if bool(params.get("check", False)) and not np.array_equal(_rs_parity(block[:data_symbols], parity_symbols), block[data_symbols:]): raise ValueError("Reed-Solomon decoder detected an invalid parity check")
        decoded.append(block[:data_symbols])
    return {"out": np.concatenate(decoded).astype(np.uint8)}


def crc_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1; width = max(1, min(32, int(params.get("width", 8)))); polynomial = _parse_polynomial(params.get("polynomial", "0x07"), 0x07); init = int(params.get("init", 0)) & ((1 << width) - 1); register = init
    for bit in bits: register = ((register << 1) ^ (polynomial if ((register >> (width - 1)) & 1) ^ int(bit) else 0)) & ((1 << width) - 1)
    crc = np.array([(register >> (width - 1 - index)) & 1 for index in range(width)], dtype=np.int8)
    return {"out": np.concatenate([bits, crc]), "reference": bits.copy()}


def crc_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1) & 1; width = max(1, min(32, int(params.get("width", 8))))
    if bits.size <= width: raise ValueError("CRC frame must contain payload and checksum bits")
    return {"out": bits[:-width]}


def repetition3_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    return {"out": np.repeat(bits, 3), "reference": bits.copy()}


def repetition3_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    usable = bits[: len(bits) - len(bits) % 3].reshape(-1, 3)
    return {"out": (usable.sum(axis=1) >= 2).astype(np.int8)}


def dc_blocker(inputs, params, context):
    samples = np.asarray(inputs["in"]).reshape(-1)
    alpha = float(params.get("alpha", 0.995))
    output = np.empty_like(samples, dtype=np.result_type(samples.dtype, np.float32))
    output[0] = samples[0]
    for index in range(1, samples.size):
        output[index] = samples[index] - samples[index - 1] + alpha * output[index - 1]
    return {"out": output}


def fir_filter(inputs, params, context):
    samples = np.asarray(inputs["in"]).reshape(-1)
    taps = np.asarray([float(value.strip()) for value in str(params.get("taps", "0.25,0.5,0.25")).split(",")], dtype=float)
    return {"out": sp.signal.lfilter(taps, [1.0], samples)}


def normalize_power(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"])
    measured = xp.mean(xp.abs(samples) ** 2)
    if float(to_numpy(measured)) <= 0:
        raise ValueError("Cannot normalize a zero-power signal")
    scale = xp.sqrt(float(params.get("target_power", 1.0)) / measured)
    return {"out": samples * scale}


def _analysis_window(xp, size: int, kind: str):
    if kind == "rectangular" or size <= 1:
        return xp.ones(size, dtype=xp.float64)
    phase = 2.0 * xp.pi * xp.arange(size, dtype=xp.float64) / (size - 1)
    if kind == "hamming":
        return 0.54 - 0.46 * xp.cos(phase)
    if kind == "blackman":
        return 0.42 - 0.5 * xp.cos(phase) + 0.08 * xp.cos(2.0 * phase)
    return 0.5 - 0.5 * xp.cos(phase)


def window_function(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    window = _analysis_window(context.xp, int(samples.size), str(params.get("window", "hann")).lower())
    return {"out": samples * window}


def fft_block(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    output = context.xp.fft.fft(samples)
    if bool(params.get("normalize", False)):
        output = output / context.xp.sqrt(samples.size)
    return {"out": output}


def ifft_block(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    output = context.xp.fft.ifft(samples)
    if bool(params.get("normalize", False)):
        output = output * context.xp.sqrt(samples.size)
    return {"out": output}


def fft_shift(inputs, params, context):
    return {"out": context.xp.fft.fftshift(context.xp.asarray(inputs["in"]).reshape(-1))}


def bpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"])
    return {"out": 1.0 - 2.0 * bits.astype(context.xp.float32)}


def qpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"], dtype=context.xp.int8).reshape(-1)
    usable = bits[: bits.size - bits.size % 2].reshape(-1, 2)
    symbols = (1.0 - 2.0 * usable[:, 0]) + 1j * (1.0 - 2.0 * usable[:, 1])
    return {"out": symbols.astype(context.xp.complex64) / context.xp.sqrt(2.0)}


def ook_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"], dtype=context.xp.float32).reshape(-1)
    return {"out": bits}


def psk8_mod(inputs, params, context):
    xp = context.xp
    bits = xp.asarray(inputs["in"], dtype=xp.int8).reshape(-1, 3)
    gray = (bits[:, 0].astype(xp.int16) << 2) | (bits[:, 1].astype(xp.int16) << 1) | bits[:, 2].astype(xp.int16)
    phase_index = gray ^ (gray >> 1) ^ (gray >> 2)
    phase = (2.0 * xp.pi / 8.0) * phase_index
    return {"out": xp.exp(1j * phase).astype(xp.complex64)}


def qam16_mod(inputs, params, context):
    xp = context.xp
    bits = xp.asarray(inputs["in"], dtype=xp.int8).reshape(-1, 4)
    levels = xp.asarray([-3.0, -1.0, 3.0, 1.0], dtype=xp.float32)
    i_index = (bits[:, 0].astype(xp.int16) << 1) | bits[:, 1].astype(xp.int16)
    q_index = (bits[:, 2].astype(xp.int16) << 1) | bits[:, 3].astype(xp.int16)
    symbols = levels[i_index] + 1j * levels[q_index]
    return {"out": symbols.astype(xp.complex64) / xp.sqrt(10.0)}


def fsk2_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"], dtype=context.xp.int8).reshape(-1)
    return {"out": context.xp.where(bits == 0, 1.0 + 0.0j, 0.0 + 1.0j).astype(context.xp.complex64)}


def awgn(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    # Legacy projects without snr_mode keep their fixed Eb/N0 behavior.
    mode = params.get("snr_mode", "fixed")
    ebn0_db = float(params.get("ebn0_db", 4.0)) if mode == "fixed" or context.snr_db is None else float(context.snr_db)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    random = _block_rng(params, context, context.xp)
    # Complex baseband signals need independent I/Q noise. Adding a real
    # array to a complex signal only perturbs I, which collapses a QPSK
    # constellation into two horizontal bands instead of four clouds.
    if context.xp.iscomplexobj(samples):
        noise = sigma * (random.normal(0.0, 1.0, samples.shape) + 1j * random.normal(0.0, 1.0, samples.shape))
    else:
        noise = random.normal(0.0, sigma, samples.shape)
    return {"out": samples + noise}


def rayleigh(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    ebn0_db = float(params.get("ebn0_db", 4.0)) if params.get("snr_mode", "fixed") == "fixed" or context.snr_db is None else float(context.snr_db)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    random = _block_rng(params, context, context.xp)
    fading = (random.normal(0.0, 1.0, samples.shape) + 1j * random.normal(0.0, 1.0, samples.shape)) / (2.0 ** 0.5)
    noise = random.normal(0.0, sigma, samples.shape) + 1j * random.normal(0.0, sigma, samples.shape)
    return {"out": samples * fading + noise}


def rician(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"])
    ebn0_db = float(params.get("ebn0_db", 4.0)) if params.get("snr_mode", "fixed") == "fixed" or context.snr_db is None else float(context.snr_db)
    k_linear = 10.0 ** (float(params.get("k_factor_db", 6.0)) / 10.0)
    random = _block_rng(params, context, xp)
    shape = (1,) if bool(params.get("flat", False)) else samples.shape
    scatter = (random.normal(0.0, 1.0, shape) + 1j * random.normal(0.0, 1.0, shape)) / (2.0 ** 0.5)
    fading = (k_linear / (k_linear + 1.0)) ** 0.5 + scatter / ((k_linear + 1.0) ** 0.5)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    noise = sigma * (random.normal(0.0, 1.0, samples.shape) + 1j * random.normal(0.0, 1.0, samples.shape))
    return {"out": samples * fading + noise}


def bpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    return {"out": (samples < 0).astype(context.xp.int8)}


def qpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    bits = context.xp.empty(samples.size * 2, dtype=context.xp.int8)
    bits[0::2] = (context.xp.real(samples) < 0).astype(context.xp.int8)
    bits[1::2] = (context.xp.imag(samples) < 0).astype(context.xp.int8)
    return {"out": bits}


def ook_demod(inputs, params, context):
    samples = context.xp.real(context.xp.asarray(inputs["in"]).reshape(-1))
    return {"out": (samples >= 0.5).astype(context.xp.int8)}


def psk8_demod(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"]).reshape(-1)
    phase_index = xp.rint(xp.mod(xp.angle(samples), 2.0 * xp.pi) * (8.0 / (2.0 * xp.pi))).astype(xp.int16) % 8
    gray = phase_index ^ (phase_index >> 1)
    bits = xp.empty(samples.size * 3, dtype=xp.int8)
    bits[0::3] = (gray >> 2) & 1
    bits[1::3] = (gray >> 1) & 1
    bits[2::3] = gray & 1
    return {"out": bits}


def qam16_demod(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"]).reshape(-1) * xp.sqrt(10.0)
    i_values = xp.real(samples)
    q_values = xp.imag(samples)
    bits = xp.empty(samples.size * 4, dtype=xp.int8)
    bits[0::4] = (i_values > 0).astype(xp.int8)
    bits[1::4] = (xp.abs(i_values) < 2.0).astype(xp.int8)
    bits[2::4] = (q_values > 0).astype(xp.int8)
    bits[3::4] = (xp.abs(q_values) < 2.0).astype(xp.int8)
    return {"out": bits}


def fsk2_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    distance_zero = context.xp.abs(samples - (1.0 + 0.0j))
    distance_one = context.xp.abs(samples - (0.0 + 1.0j))
    return {"out": (distance_one < distance_zero).astype(context.xp.int8)}


def hamming74_decode(inputs, params, context):
    received = to_numpy(inputs["in"]).astype(np.int8).reshape(-1)
    received = received.reshape(-1, 7).copy()
    if not len(received):
        return {"out": np.array([], dtype=np.int8)}
    s1 = received[:, 0] ^ received[:, 1] ^ received[:, 3] ^ received[:, 4]
    s2 = received[:, 0] ^ received[:, 2] ^ received[:, 3] ^ received[:, 5]
    s3 = received[:, 1] ^ received[:, 2] ^ received[:, 3] ^ received[:, 6]
    syndromes = s1 + 2 * s2 + 4 * s3
    # Map the non-zero syndrome to its coordinate in [d1,d2,d3,d4,p1,p2,p3].
    error_indices = np.array([-1, 4, 5, 0, 6, 1, 2, 3], dtype=np.int8)
    rows = np.flatnonzero(syndromes)
    received[rows, error_indices[syndromes[rows]]] ^= 1
    return {"out": received[:, :4].reshape(-1)}


def ber(inputs, params, context):
    reference = to_numpy(inputs["reference"]).astype(np.int8).reshape(-1)
    estimate = to_numpy(inputs["estimate"]).astype(np.int8).reshape(-1)
    count = min(len(reference), len(estimate))
    errors = int(np.count_nonzero(reference[:count] != estimate[:count]))
    return {"__metrics__": {"bit_errors": errors, "total_bits": count}}


def ser(inputs, params, context):
    reference = np.asarray(inputs["reference"]).astype(str).reshape(-1)
    estimate = np.asarray(inputs["estimate"]).astype(str).reshape(-1)
    errors = int(np.count_nonzero(reference != estimate))
    return {"__metrics__": {"symbol_errors": errors, "total_symbols": len(reference)}}


def scope(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    if not len(samples):
        return {"__metrics__": {"scope_count": 0}}
    amplitude = np.abs(samples)
    return {"__metrics__": {"scope_count": int(len(samples)), "scope_sum": float(amplitude.sum()), "scope_peak": float(amplitude.max())}}


def constellation(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    if not len(samples):
        return {"__metrics__": {"constellation_count": 0}}
    return {"__metrics__": {
        "constellation_count": int(len(samples)),
        "constellation_i_sum": float(np.real(samples).sum()),
        "constellation_q_sum": float(np.imag(samples).sum()),
        "constellation_power_sum": float(np.abs(samples).sum()),
    }}


def power_meter(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    return {"__metrics__": {"power_count": int(len(samples)), "power_sum": float(np.abs(samples).astype(float).dot(np.abs(samples).astype(float))) if len(samples) else 0.0}}


def _spectrum_db(samples, fft_size: int, window: str):
    values = np.asarray(samples).reshape(-1)
    segment = np.zeros(fft_size, dtype=np.complex128)
    count = min(values.size, fft_size)
    segment[:count] = values[:count]
    weights = np.asarray(_analysis_window(np, fft_size, window))
    weighted = segment * weights
    magnitude = np.abs(np.fft.fftshift(np.fft.fft(weighted))) / max(1.0, float(weights.sum()))
    return 20.0 * np.log10(np.maximum(magnitude, np.finfo(float).tiny))


def spectrum_analyzer(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    fft_size = int(params.get("fft_size", 256))
    spectrum = _spectrum_db(samples, fft_size, str(params.get("window", "hann")).lower())
    peak_index = int(np.argmax(spectrum))
    return {"__metrics__": {
        "spectrum_frame_count": 1,
        "spectrum_peak_db_sum": float(spectrum[peak_index]),
        "spectrum_floor_db_sum": float(np.median(spectrum)),
        "spectrum_peak_normalized_sum": float((peak_index - fft_size / 2) / fft_size),
    }}


def waterfall_sink(inputs, params, context):
    samples = to_numpy(inputs["in"]).reshape(-1)
    fft_size = int(params.get("fft_size", 64))
    window = str(params.get("window", "hann")).lower()
    row_count = max(1, min(32, math.ceil(samples.size / fft_size)))
    rows = [_spectrum_db(samples[start:start + fft_size], fft_size, window) for start in range(0, row_count * fft_size, fft_size)]
    values = np.concatenate(rows)
    return {"__metrics__": {
        "waterfall_frame_count": 1,
        "waterfall_peak_db_sum": float(np.max(values)),
        "waterfall_floor_db_sum": float(np.median(values)),
        "waterfall_rows_sum": row_count,
    }}


def evm_meter(inputs, params, context):
    reference = to_numpy(inputs["reference"]).reshape(-1)
    estimate = to_numpy(inputs["estimate"]).reshape(-1)
    error = estimate - reference
    return {"__metrics__": {
        "evm_error_energy": float(np.vdot(error, error).real),
        "evm_reference_energy": float(np.vdot(reference, reference).real),
        "evm_symbol_count": int(reference.size),
    }}


def variables_block(inputs, params, context):
    return {}


@lru_cache(maxsize=128)
def _compile_python_block(code: str):
    return compile(code, "<python-block>", "exec")


@lru_cache(maxsize=256)
def _python_function_profile(code_object) -> tuple[int, bool, str]:
    positional_count = int(code_object.co_argcount)
    has_varargs = bool(code_object.co_flags & inspect.CO_VARARGS)
    first_name = str(code_object.co_varnames[0]).lower() if positional_count else ""
    return positional_count, has_varargs, first_name


@lru_cache(maxsize=256)
def python_has_batch(code: str | None) -> bool:
    try:
        tree = ast.parse(str(code or ""), filename="<python-block>", mode="exec")
    except SyntaxError:
        return False
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "process_batch" for node in tree.body)


def _runtime_params(params, context) -> dict[str, Any]:
    global_values = copy.deepcopy(getattr(context, "global_variables", {}))
    experiment = {
        "snr_db": context.snr_db,
        "trial_index": context.trial_index,
        "seed": context.seed,
        "device": context.device,
    }
    return {
        **global_values,
        **copy.deepcopy(params),
        "snr_db": context.snr_db,
        "trial_index": context.trial_index,
        "frame_seed": context.seed,
        "device": context.device,
        "experiment": experiment,
        "variables": copy.deepcopy(global_values),
    }


def _callable_profile(process) -> tuple[int, bool, str]:
    if inspect.isfunction(process):
        return _python_function_profile(process.__code__)
    signature = inspect.signature(process)
    positional = [parameter for parameter in signature.parameters.values() if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)]
    return (
        len(positional),
        any(parameter.kind == parameter.VAR_POSITIONAL for parameter in signature.parameters.values()),
        positional[0].name.lower() if positional else "",
    )


def python_block(inputs, params, context, code):
    if not code:
        return {"out": inputs.get("in")}
    ports = parse_python_ports(code)
    namespace = {
        "PORTS": {"inputs": ports.inputs.copy(), "outputs": ports.outputs.copy()},
        "np": np,
        "numpy": np,
        "sp": sp,
        "scipy": sp,
        "sl": sl,
        "signallab": sl,
        "signal": inputs.get("in"),
        "__builtins__": __builtins__,
    }
    try:
        exec(_compile_python_block(code), namespace, namespace)
    except Exception as exc:
        raise ValueError(_python_process_error(exc, code, {}, ports.inputs)) from exc
    process = namespace.get("process")
    if not callable(process):
        raise ValueError("Python block must define process(signal, params)")
    signal = inputs.get("in")
    runtime_params = _runtime_params(params, context)
    positional_count, has_varargs, first_parameter_name = _callable_profile(process)
    try:
        if has_varargs or positional_count >= 3:
            # Backward-compatible form: process(inputs, params, context) -> {"out": ...}
            result = process(inputs, runtime_params, context)
        elif ports.explicit:
            # Explicit PORTS use a named input mapping. A source with no inputs
            # may use the natural process(params) form, which is especially
            # useful for generators driven entirely by Variables/Experiment.
            if positional_count >= 2:
                result = process(inputs, runtime_params)
            elif positional_count == 1:
                result = process(runtime_params if not ports.inputs and first_parameter_name in {"params", "config", "runtime_params"} else inputs)
            else:
                result = process()
        elif positional_count == 2:
            # Recommended form: process(signal, params) -> array
            result = process(signal, runtime_params)
        elif positional_count == 1:
            result = process(signal)
        else:
            result = process()
    except Exception as exc:
        raise ValueError(_python_process_error(exc, code, runtime_params, ports.inputs)) from exc
    if isinstance(result, dict):
        return result
    if result is None:
        if ports.outputs:
            raise ValueError("Python block process() must return a signal array or output dictionary")
        return {}
    if len(ports.outputs) != 1:
        raise ValueError("A Python Block with multiple output ports must return a dictionary keyed by port name")
    return {ports.outputs[0]: result}


def _stack_python_batch(values: list[Any]) -> Any:
    arrays = [np.asarray(value) for value in values]
    if arrays and all(array.shape == arrays[0].shape and array.dtype == arrays[0].dtype for array in arrays[1:]):
        return np.stack(arrays, axis=0)
    return values


def _split_python_batch(value: Any, count: int, port: str) -> list[Any]:
    if isinstance(value, (list, tuple)):
        if len(value) != count:
            raise ValueError(f"Python process_batch() output '{port}' returned {len(value)} frames; expected {count}")
        return list(value)
    array = np.asarray(value)
    if array.ndim < 2 or array.shape[0] != count:
        raise ValueError(
            f"Python process_batch() output '{port}' must have a leading frame dimension of {count}; received shape {array.shape}"
        )
    return [array[index] for index in range(count)]


def python_block_batch(inputs_batch: list[dict[str, Any]], params, contexts: list[Any], code: str) -> list[dict[str, Any]]:
    """Run an opt-in vectorized Python block once for a scheduler chunk."""
    if not inputs_batch or len(inputs_batch) != len(contexts):
        raise ValueError("Python process_batch() requires one input mapping per frame")
    ports = parse_python_ports(code)
    namespace = {
        "PORTS": {"inputs": ports.inputs.copy(), "outputs": ports.outputs.copy()},
        "np": np,
        "numpy": np,
        "sp": sp,
        "scipy": sp,
        "sl": sl,
        "signallab": sl,
        "__builtins__": __builtins__,
    }
    try:
        exec(_compile_python_block(code), namespace, namespace)
    except Exception as exc:
        raise ValueError(_python_process_error(exc, code, {}, ports.inputs)) from exc
    process_batch = namespace.get("process_batch")
    if not callable(process_batch):
        raise ValueError("Python block batch path requires process_batch(signals, params_batch)")
    batched_inputs = {name: _stack_python_batch([frame[name] for frame in inputs_batch]) for name in ports.inputs}
    signals = batched_inputs if ports.explicit else batched_inputs.get("in")
    params_batch = [_runtime_params(params, context) for context in contexts]
    positional_count, has_varargs, _ = _callable_profile(process_batch)
    try:
        if has_varargs or positional_count >= 3:
            raw = process_batch(signals, params_batch, contexts)
        elif positional_count == 2:
            raw = process_batch(signals, params_batch)
        elif positional_count == 1:
            raw = process_batch(signals)
        else:
            raw = process_batch()
    except Exception as exc:
        raise ValueError(_python_process_error(exc, code, params_batch[0], ports.inputs).replace("process()", "process_batch()")) from exc
    if isinstance(raw, dict):
        batched_outputs = raw
    elif len(ports.outputs) == 1:
        batched_outputs = {ports.outputs[0]: raw}
    elif raw is None and not ports.outputs:
        batched_outputs = {}
    else:
        raise ValueError("Python process_batch() with multiple outputs must return a dictionary")
    if set(batched_outputs) != set(ports.outputs):
        raise ValueError("Python process_batch() outputs must match the declared PORTS exactly")
    split = {port: _split_python_batch(value, len(contexts), port) for port, value in batched_outputs.items()}
    return [{port: values[index] for port, values in split.items()} for index in range(len(contexts))]


def _python_process_error(exc: Exception, code: str, runtime_params: dict[str, Any], input_ports: list[str]) -> str:
    """Turn a Python exception into an actionable classroom-friendly message."""
    location = ""
    traceback_items = traceback.extract_tb(exc.__traceback__)
    block_frames = [item for item in traceback_items if item.filename == "<python-block>"]
    if block_frames:
        frame = block_frames[-1]
        source_line = code.splitlines()[frame.lineno - 1].strip() if frame.lineno and frame.lineno <= len(code.splitlines()) else ""
        location = f" at line {frame.lineno}"
        if source_line:
            location += f" ({source_line})"
    if isinstance(exc, KeyError) and exc.args:
        missing = str(exc.args[0])
        available = ", ".join(sorted(str(key) for key in runtime_params)) or "none"
        hint = " Add it in the Variables block or use params.get(...)." if not input_ports else " Check the input port name or add the parameter in Variables."
        return f"Python process() failed{location}: missing key {missing!r}. Available params: {available}.{hint}"
    return f"Python process() failed{location}: {type(exc).__name__}: {exc}"


PROCESSORS: dict[str, Callable] = {
    "variables": variables_block,
    "bit_source": bit_source,
    "text_source": text_source,
    "text_file_source": text_file_source,
    "text_symbol_source": text_symbol_source,
    "text_file_symbol_source": text_file_symbol_source,
    "discrete_symbol_source": discrete_symbol_source,
    "source_analyzer": source_analyzer,
    "symbols_to_bits": symbols_to_bits,
    "image_file_source": image_file_source,
    "differential_encode": differential_encode,
    "differential_decode": differential_decode,
    "convolutional_encode": convolutional_encode,
    "viterbi_decode": viterbi_decode,
    "huffman_encode": huffman_encode,
    "huffman_decode": huffman_decode,
    "shannon_fano_encode": shannon_fano_encode,
    "shannon_fano_decode": shannon_fano_decode,
    "symbol_huffman_encode": symbol_huffman_encode,
    "symbol_huffman_decode": symbol_huffman_decode,
    "symbol_shannon_fano_encode": symbol_shannon_fano_encode,
    "symbol_shannon_fano_decode": symbol_shannon_fano_decode,
    "rle_encode": rle_encode,
    "rle_decode": rle_decode,
    "zip_encode": zip_encode,
    "zip_decode": zip_decode,
    "hamming74_encode": hamming74_encode,
    "cyclic_encode": cyclic_encode,
    "cyclic_decode": cyclic_decode,
    "bch_encode": bch_encode,
    "bch_decode": bch_decode,
    "reed_solomon_encode": reed_solomon_encode,
    "reed_solomon_decode": reed_solomon_decode,
    "crc_encode": crc_encode,
    "crc_decode": crc_decode,
    "repetition3_encode": repetition3_encode,
    "repetition3_decode": repetition3_decode,
    "dc_blocker": dc_blocker,
    "fir_filter": fir_filter,
    "normalize_power": normalize_power,
    "window_function": window_function,
    "fft": fft_block,
    "ifft": ifft_block,
    "fft_shift": fft_shift,
    "bpsk_mod": bpsk_mod,
    "qpsk_mod": qpsk_mod,
    "ook_mod": ook_mod,
    "psk8_mod": psk8_mod,
    "qam16_mod": qam16_mod,
    "fsk2_mod": fsk2_mod,
    "awgn": awgn,
    "rayleigh": rayleigh,
    "rician": rician,
    "bpsk_demod": bpsk_demod,
    "qpsk_demod": qpsk_demod,
    "ook_demod": ook_demod,
    "psk8_demod": psk8_demod,
    "qam16_demod": qam16_demod,
    "fsk2_demod": fsk2_demod,
    "hamming74_decode": hamming74_decode,
    "scope": scope,
    "constellation": constellation,
    "power_meter": power_meter,
    "spectrum_analyzer": spectrum_analyzer,
    "waterfall_sink": waterfall_sink,
    "evm_meter": evm_meter,
    "ber": ber,
    "ser": ser,
}


def to_numpy(value):
    if isinstance(value, np.ndarray):
        return value
    if hasattr(value, "get"):
        return value.get()
    return np.asarray(value)


def make_context(
    xp,
    rng,
    trial_index: int,
    seed: int,
    device: str,
    snr_db: float | None = None,
    random_seed_root: int | None = None,
    global_variables: dict[str, Any] | None = None,
):
    return SimpleNamespace(
        xp=xp,
        rng=rng,
        trial_index=trial_index,
        seed=seed,
        device=device,
        snr_db=snr_db,
        random_seed_root=secrets.randbits(64) if random_seed_root is None else random_seed_root,
        global_variables={} if global_variables is None else global_variables,
        node_id="",
    )
