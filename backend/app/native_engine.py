from __future__ import annotations

import os
import secrets
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import Graph, SimulationConfig


_DLL_HANDLES: list[Any] = []
_NATIVE_MODULE: Any | None = None
_NATIVE_ERROR: str | None = None


def _load_native() -> Any | None:
    global _NATIVE_MODULE, _NATIVE_ERROR
    if _NATIVE_MODULE is not None:
        return _NATIVE_MODULE
    if _NATIVE_ERROR is not None:
        return None
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        candidates = [
            Path(__file__).resolve().parent,
            Path(__file__).resolve().parents[2] / ".venv" / "Library" / "bin",
        ]
        for candidate in candidates:
            if candidate.is_dir():
                try:
                    _DLL_HANDLES.append(os.add_dll_directory(str(candidate)))
                except OSError:
                    pass
    try:
        from . import _native_core

        _NATIVE_MODULE = _native_core
        return _NATIVE_MODULE
    except Exception as exc:  # Native support is optional and must fall back cleanly.
        _NATIVE_ERROR = str(exc)
        return None


def native_status() -> dict[str, Any]:
    native = _load_native()
    if native is None:
        return {
            "available": False,
            "backend": "python_numpy",
            "reason": _NATIVE_ERROR or "Native module has not been built",
        }
    return {
        "available": True,
        "backend": "cpp_onetbb",
        "version": str(getattr(native, "__version__", "unknown")),
        "features": ["fused-bpsk-awgn", "fused-qpsk-awgn", "fused-qam16-awgn", "hamming74", "repetition3", "philox", "single-machine-threading"],
    }


@dataclass(frozen=True)
class NativePlan:
    bit_length: int
    coding: str
    modulation: str
    source_seed: int
    noise_seed: int
    awgn_fixed_snr: float | None


def _edge_set(graph: Graph) -> set[tuple[str, str, str, str]]:
    return {
        (edge.source, edge.source_handle, edge.target, edge.target_handle)
        for edge in graph.edges
    }


def _match_unique_types(graph: Graph, expected: list[str]) -> dict[str, Any] | None:
    if len(graph.nodes) != len(expected) or sorted(node.type for node in graph.nodes) != sorted(expected):
        return None
    by_type = {node.type: node for node in graph.nodes}
    return by_type if len(by_type) == len(expected) else None


def _match_pipeline(graph: Graph, modulation: str, coding: str) -> dict[str, Any] | None:
    modulator, demodulator = {
        "bpsk": ("bpsk_mod", "bpsk_demod"),
        "qpsk": ("qpsk_mod", "qpsk_demod"),
        "qam16": ("qam16_mod", "qam16_demod"),
    }[modulation]
    coding_types = {
        "none": [],
        "hamming74": ["hamming74_encode", "hamming74_decode"],
        "repetition3": ["repetition3_encode", "repetition3_decode"],
    }[coding]
    return _match_unique_types(
        graph,
        ["bit_source", modulator, "awgn", demodulator, "ber", *coding_types],
    )


def _seed_key(base_seed: int, experiment_seed: int, node_id: str) -> int:
    value = (int(base_seed) & 0xFFFFFFFFFFFFFFFF) ^ ((int(experiment_seed) & 0xFFFFFFFF) << 32)
    value ^= zlib.crc32(node_id.encode("utf-8"))
    value = (value + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return value ^ (value >> 31)


def compile_native_plan(graph: Graph, config: SimulationConfig) -> tuple[NativePlan | None, str | None]:
    if _load_native() is None:
        return None, _NATIVE_ERROR or "Native module is unavailable"
    if config.device == "gpu":
        return None, "The native v0.2 plan currently targets CPU only"

    by_type = None
    modulation = "bpsk"
    coding = "none"
    for candidate_modulation, candidate_coding in (
        ("bpsk", "hamming74"),
        ("bpsk", "repetition3"),
        ("bpsk", "none"),
        ("qpsk", "hamming74"),
        ("qpsk", "repetition3"),
        ("qpsk", "none"),
        ("qam16", "none"),
    ):
        by_type = _match_pipeline(graph, candidate_modulation, candidate_coding)
        if by_type is not None:
            modulation, coding = candidate_modulation, candidate_coding
            break
    if by_type is None:
        return None, "Native v0.2 supports exact AWGN/BER chains using BPSK, QPSK, or uncoded 16-QAM"

    source = by_type["bit_source"]
    modulator = by_type[f"{modulation}_mod"]
    channel = by_type["awgn"]
    demodulator = by_type[f"{modulation}_demod"]
    meter = by_type["ber"]
    if coding == "hamming74":
        encoder, decoder = by_type["hamming74_encode"], by_type["hamming74_decode"]
    elif coding == "repetition3":
        encoder, decoder = by_type["repetition3_encode"], by_type["repetition3_decode"]
    else:
        encoder = decoder = None
    required = {
        (source.id, "out", encoder.id, "in") if encoder else (source.id, "out", modulator.id, "in"),
        (encoder.id, "out", modulator.id, "in") if encoder else (modulator.id, "out", channel.id, "in"),
        (modulator.id, "out", channel.id, "in"),
        (channel.id, "out", demodulator.id, "in"),
        (demodulator.id, "out", decoder.id, "in") if decoder else (demodulator.id, "out", meter.id, "estimate"),
        (encoder.id, "reference", meter.id, "reference") if encoder else (source.id, "out", meter.id, "reference"),
        (decoder.id, "out", meter.id, "estimate") if decoder else (demodulator.id, "out", meter.id, "estimate"),
    }
    if required != _edge_set(graph):
        return None, "The supported native blocks must form one exact modulation/AWGN/BER chain without extra edges"

    bit_length = int(source.params.get("length", 4096))
    if coding == "hamming74" and bit_length % 4:
        return None, "Native Hamming execution requires the Bit Source length to be divisible by 4"
    coded_length = bit_length if coding == "none" else bit_length * 3 if coding == "repetition3" else bit_length // 4 * 7
    bits_per_symbol = {"bpsk": 1, "qpsk": 2, "qam16": 4}[modulation]
    if coded_length % bits_per_symbol:
        return None, f"Native {modulation.upper()} execution requires the coded bit count to be divisible by {bits_per_symbol}"
    random_root = secrets.randbits(64)
    source_base = random_root if int(source.params.get("seed", -1)) == -1 else int(source.params.get("seed", -1))
    noise_base = random_root if int(channel.params.get("seed", -1)) == -1 else int(channel.params.get("seed", -1))
    fixed_snr = float(channel.params.get("ebn0_db", 4.0)) if channel.params.get("snr_mode", "fixed") == "fixed" else None
    return NativePlan(
        bit_length=bit_length,
        coding=coding,
        modulation=modulation,
        source_seed=_seed_key(source_base, config.seed, source.id),
        noise_seed=_seed_key(noise_base, config.seed, channel.id),
        awgn_fixed_snr=fixed_snr,
    ), None


def _snr_values(config: SimulationConfig) -> list[float]:
    if config.mode == "specific_steps":
        return [round(float(config.snr_db_start), 6)]
    values: list[float] = []
    value = float(config.snr_db_start)
    while value <= float(config.snr_db_stop) + float(config.snr_db_step) * 0.5:
        values.append(round(value, 6))
        value += float(config.snr_db_step)
    return values or [round(float(config.snr_db_start), 6)]


def run_native_simulation(
    graph: Graph,
    config: SimulationConfig,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    plan, reason = compile_native_plan(graph, config)
    if plan is None:
        return None, reason
    native = _load_native()
    assert native is not None

    started = time.perf_counter()
    max_frames = config.max_frames or config.trials
    min_frames = min(config.min_frames, max_frames)
    snr_values = _snr_values(config)
    cpu_count = os.cpu_count() or 1
    total_work = plan.bit_length * max_frames
    workers = min(cpu_count, max_frames if plan.bit_length < 262_144 else cpu_count)
    if config.workers:
        workers = min(max(1, config.workers), cpu_count)
    elif total_work < 1_000_000:
        workers = 1

    aggregate: dict[str, int] = {"bit_errors": 0, "total_bits": 0, "completed_trials": 0}
    points: list[dict[str, Any]] = []
    total_budget = len(snr_values) * max_frames
    was_cancelled = False
    target_bits_per_tile = 8 * 1024 * 1024
    tile_floor = max(1, config.chunk_size * workers)

    for snr_index, requested_snr in enumerate(snr_values):
        effective_snr = plan.awgn_fixed_snr if plan.awgn_fixed_snr is not None else requested_snr
        point: dict[str, int] = {"bit_errors": 0, "total_bits": 0, "frames": 0}
        while point["frames"] < max_frames:
            if cancelled and cancelled():
                was_cancelled = True
                break
            remaining = max_frames - int(point["frames"])
            if config.mode == "ber_benchmark":
                frames_to_minimum = max(0, min_frames - int(point["frames"]))
                # Reach the minimum exactly, then retain chunk-granular early
                # stopping instead of consuming the entire SNR budget at once.
                requested_tile = frames_to_minimum if frames_to_minimum else tile_floor
            else:
                requested_tile = max(tile_floor, target_bits_per_tile // max(1, plan.bit_length))
            # Logical frames can deliberately be tiny for teaching/debugging
            # (e.g. one four-bit Hamming message). Keep that public boundary,
            # but amortize Python/pybind/TBB overhead with a bounded native tile.
            tile_frames = min(remaining, max(1, min(262_144, requested_tile)))
            result = native.run_modulated_awgn_batch(
                plan.bit_length,
                int(point["frames"]),
                tile_frames,
                effective_snr,
                plan.source_seed ^ snr_index,
                plan.noise_seed ^ snr_index,
                workers,
                {"none": 0, "hamming74": 1, "repetition3": 2}[plan.coding],
                {"bpsk": 0, "qpsk": 1, "qam16": 2}[plan.modulation],
            )
            point["bit_errors"] += int(result["bit_errors"])
            point["total_bits"] += int(result["total_bits"])
            point["frames"] += int(result["completed_trials"])
            aggregate["bit_errors"] += int(result["bit_errors"])
            aggregate["total_bits"] += int(result["total_bits"])
            aggregate["completed_trials"] += int(result["completed_trials"])
            live = [*points, {
                "snr_db": requested_snr,
                "bit_errors": point["bit_errors"],
                "total_bits": point["total_bits"],
                "frames": point["frames"],
                "ber": point["bit_errors"] / point["total_bits"] if point["total_bits"] else None,
            }]
            if progress:
                progress({
                    **aggregate,
                    "trials": total_budget,
                    "device": "cpu",
                    "engine": "native_cpp",
                    "workers": workers,
                    "snr_db": requested_snr,
                    "snr_index": snr_index,
                    "snr_count": len(snr_values),
                    "snr_points": live,
                })
            stop = point["frames"] >= max_frames
            if config.mode == "ber_benchmark":
                stop = point["frames"] >= min_frames and (
                    point["bit_errors"] >= config.min_errors or point["frames"] >= max_frames
                )
            if stop:
                break
        points.append({
            "snr_db": requested_snr,
            "bit_errors": point["bit_errors"],
            "total_bits": point["total_bits"],
            "frames": point["frames"],
            "ber": point["bit_errors"] / point["total_bits"] if point["total_bits"] else None,
        })
        if was_cancelled:
            break

    elapsed = time.perf_counter() - started
    bits = aggregate["total_bits"]
    return {
        **aggregate,
        "ber": aggregate["bit_errors"] / bits if bits else None,
        "elapsed_seconds": elapsed,
        "throughput_bps": bits / elapsed if elapsed else 0,
        "device": "cpu",
        "engine": "native_cpp",
        "workers": workers,
        "cancelled": was_cancelled,
        "snr_points": points,
        "sink_metrics": {},
        "execution": {
            "backend": "cpp_onetbb",
            "version": str(getattr(native, "__version__", "unknown")),
            "modulation": plan.modulation,
            "coding": plan.coding,
            "kernel": "fused_metric_only",
        },
        "warnings": [],
    }, None
