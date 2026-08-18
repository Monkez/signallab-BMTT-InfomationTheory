from __future__ import annotations

import base64
import heapq
import inspect
import secrets
import zlib
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np
import scipy as sp

import signallab as sl


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


def repetition3_encode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    return {"out": np.repeat(bits, 3), "reference": bits.copy()}


def repetition3_decode(inputs, params, context):
    bits = np.asarray(inputs["in"], dtype=np.int8).reshape(-1)
    usable = bits[: len(bits) - len(bits) % 3].reshape(-1, 3)
    return {"out": (usable.sum(axis=1) >= 2).astype(np.int8)}


def bpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"])
    return {"out": 1.0 - 2.0 * bits.astype(context.xp.float32)}


def qpsk_mod(inputs, params, context):
    bits = context.xp.asarray(inputs["in"], dtype=context.xp.int8).reshape(-1)
    usable = bits[: bits.size - bits.size % 2].reshape(-1, 2)
    symbols = (1.0 - 2.0 * usable[:, 0]) + 1j * (1.0 - 2.0 * usable[:, 1])
    return {"out": symbols.astype(context.xp.complex64) / context.xp.sqrt(2.0)}


def awgn(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    # Legacy projects without snr_mode keep their fixed Eb/N0 behavior.
    mode = params.get("snr_mode", "fixed")
    ebn0_db = float(params.get("ebn0_db", 4.0)) if mode == "fixed" or context.snr_db is None else float(context.snr_db)
    sigma = (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
    random = _block_rng(params, context, context.xp)
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


def bpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"])
    return {"out": (samples < 0).astype(context.xp.int8)}


def qpsk_demod(inputs, params, context):
    samples = context.xp.asarray(inputs["in"]).reshape(-1)
    bits = context.xp.empty(samples.size * 2, dtype=context.xp.int8)
    bits[0::2] = (context.xp.real(samples) < 0).astype(context.xp.int8)
    bits[1::2] = (context.xp.imag(samples) < 0).astype(context.xp.int8)
    return {"out": bits}


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


def python_block(inputs, params, context, code):
    if not code:
        return {"out": inputs.get("in")}
    namespace = {
        "np": np,
        "numpy": np,
        "sp": sp,
        "scipy": sp,
        "sl": sl,
        "signallab": sl,
        "signal": inputs.get("in"),
        "__builtins__": __builtins__,
    }
    exec(compile(code, "<python-block>", "exec"), namespace, namespace)
    process = namespace.get("process")
    if not callable(process):
        raise ValueError("Python block must define process(signal, params)")
    signal = inputs.get("in")
    positional = [parameter for parameter in inspect.signature(process).parameters.values() if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(parameter.kind == parameter.VAR_POSITIONAL for parameter in inspect.signature(process).parameters.values())
    if has_varargs or len(positional) >= 3:
        # Backward-compatible form: process(inputs, params, context) -> {"out": ...}
        result = process(inputs, params, context)
    elif len(positional) == 2:
        # Recommended form: process(signal, params) -> array
        result = process(signal, params)
    elif len(positional) == 1:
        result = process(signal)
    else:
        result = process()
    if isinstance(result, dict):
        if "out" not in result:
            raise ValueError("A Python block dictionary result must contain an 'out' key")
        return result
    if result is None:
        raise ValueError("Python block process() must return a signal array")
    return {"out": result}


PROCESSORS: dict[str, Callable] = {
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
    "repetition3_encode": repetition3_encode,
    "repetition3_decode": repetition3_decode,
    "bpsk_mod": bpsk_mod,
    "qpsk_mod": qpsk_mod,
    "awgn": awgn,
    "rayleigh": rayleigh,
    "bpsk_demod": bpsk_demod,
    "qpsk_demod": qpsk_demod,
    "hamming74_decode": hamming74_decode,
    "scope": scope,
    "constellation": constellation,
    "power_meter": power_meter,
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
):
    return SimpleNamespace(
        xp=xp,
        rng=rng,
        trial_index=trial_index,
        seed=seed,
        device=device,
        snr_db=snr_db,
        random_seed_root=secrets.randbits(64) if random_seed_root is None else random_seed_root,
        node_id="",
    )
