from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .blocks import PROCESSORS, SPEC_BY_TYPE, make_context, python_block
from .models import Graph, SimulationConfig, ValidationResult


def gpu_status() -> dict[str, Any]:
    try:
        import cupy as cp
        count = int(cp.cuda.runtime.getDeviceCount())
        if count:
            name = cp.cuda.runtime.getDeviceProperties(0)["name"]
            if isinstance(name, bytes):
                name = name.decode()
            return {"available": True, "count": count, "name": name}
    except Exception as exc:
        return {"available": False, "count": 0, "reason": str(exc)}
    return {"available": False, "count": 0, "reason": "No CUDA device found"}


def validate_graph(graph: Graph) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    node_map = {node.id: node for node in graph.nodes}
    if not graph.nodes:
        errors.append("Graph has no blocks")
    for node in graph.nodes:
        if node.type not in SPEC_BY_TYPE:
            errors.append(f"Block '{node.label}' has unknown type '{node.type}'")
    incoming: dict[str, set[str]] = {node.id: set() for node in graph.nodes}
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    indegree = {node.id: 0 for node in graph.nodes}
    for edge in graph.edges:
        if edge.source not in node_map or edge.target not in node_map:
            errors.append(f"Edge '{edge.id}' references a missing block")
            continue
        incoming[edge.target].add(edge.target_handle)
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1
    for node in graph.nodes:
        spec = SPEC_BY_TYPE.get(node.type)
        if spec:
            for port in spec.inputs:
                if port not in incoming[node.id]:
                    errors.append(f"Block '{node.label}' is missing input '{port}'")
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(graph.nodes):
        errors.append("Graph must be acyclic")
    if not any(node.type == "ber" for node in graph.nodes):
        warnings.append("Graph has no BER Meter, so no BER metric will be produced")
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def topological_order(graph_dict: dict[str, Any]) -> list[str]:
    nodes = graph_dict["nodes"]
    indegree = {node["id"]: 0 for node in nodes}
    adjacency = {node["id"]: [] for node in nodes}
    for edge in graph_dict["edges"]:
        adjacency[edge["source"]].append(edge["target"])
        indegree[edge["target"]] += 1
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    order = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return order


def execute_trial(
    graph_dict: dict[str, Any],
    trial_index: int,
    seed: int,
    device: str = "cpu",
    snr_db: float | None = None,
) -> dict[str, int]:
    xp = np
    actual_device = "cpu"
    if device == "gpu":
        try:
            import cupy as cp
            xp = cp
            actual_device = "gpu"
        except Exception:
            pass
    rng = np.random.default_rng(seed)
    context = make_context(xp, rng, trial_index, seed, actual_device, snr_db)
    nodes = {node["id"]: node for node in graph_dict["nodes"]}
    outputs: dict[str, dict[str, Any]] = {}
    metrics = {"bit_errors": 0, "total_bits": 0}
    incoming: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in nodes}
    for edge in graph_dict["edges"]:
        incoming[edge["target"]].append(edge)
    for node_id in topological_order(graph_dict):
        node = nodes[node_id]
        node_inputs = {}
        for edge in incoming[node_id]:
            node_inputs[edge.get("target_handle", "in")] = outputs[edge["source"]][edge.get("source_handle", "out")]
        if node["type"] == "python":
            result = python_block(node_inputs, node.get("params", {}), context, node.get("code"))
        else:
            result = PROCESSORS[node["type"]](node_inputs, node.get("params", {}), context)
        node_metrics = result.pop("__metrics__", None)
        if node_metrics:
            for key, value in node_metrics.items():
                metrics[key] = metrics.get(key, 0) + int(value)
        outputs[node_id] = result
    return metrics


def _run_chunk(
    graph_dict: dict[str, Any],
    items: list[tuple[int, int]],
    device: str,
    snr_db: float,
) -> dict[str, int]:
    total = {"bit_errors": 0, "total_bits": 0, "completed_trials": 0}
    for trial_index, seed in items:
        result = execute_trial(graph_dict, trial_index, seed, device, snr_db)
        total["bit_errors"] += result["bit_errors"]
        total["total_bits"] += result["total_bits"]
        total["completed_trials"] += 1
    return total


def run_simulation(
    graph: Graph,
    config: SimulationConfig,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    validation = validate_graph(graph)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    started = time.perf_counter()
    graph_dict = graph.model_dump()
    max_frames = config.max_frames or config.trials
    min_frames = min(config.min_frames, max_frames)
    if config.snr_db_stop < config.snr_db_start:
        raise ValueError("SNR stop must be greater than or equal to SNR start")
    snr_values = [
        round(float(value), 6)
        for value in np.arange(config.snr_db_start, config.snr_db_stop + config.snr_db_step * 0.5, config.snr_db_step)
    ]
    if not snr_values:
        snr_values = [round(float(config.snr_db_start), 6)]
    gpu = gpu_status()
    gpu_compatible = all(SPEC_BY_TYPE[node.type].gpu_compatible for node in graph.nodes)
    if config.device == "gpu" and not gpu["available"]:
        raise ValueError("GPU was requested but CuPy/CUDA is unavailable")
    device = "gpu" if config.device in ("gpu", "auto") and gpu["available"] and gpu_compatible else "cpu"
    cpu_count = os.cpu_count() or 1
    workers = config.workers or max(1, cpu_count - 1)
    workers = min(workers, max_frames, cpu_count)
    if device == "gpu":
        workers = 1
    aggregate = {"bit_errors": 0, "total_bits": 0, "completed_trials": 0}
    point_results: list[dict[str, Any]] = []
    total_budget = len(snr_values) * max_frames
    was_cancelled = False

    for snr_index, snr_db in enumerate(snr_values):
        point = {"bit_errors": 0, "total_bits": 0, "frames": 0}
        seed_sequence = np.random.SeedSequence([config.seed, snr_index])
        seeds = seed_sequence.spawn(max_frames)
        items = [(i, int(seed.generate_state(1)[0])) for i, seed in enumerate(seeds)]
        offset = 0
        while offset < max_frames:
            if cancelled and cancelled():
                was_cancelled = True
                break
            batch = items[offset : offset + config.chunk_size * workers]
            chunks = [batch[i : i + config.chunk_size] for i in range(0, len(batch), config.chunk_size)]
            results: list[dict[str, int]] = []
            if workers == 1 or len(batch) < max(4, config.chunk_size):
                results = [_run_chunk(graph_dict, chunk, device, snr_db) for chunk in chunks]
            else:
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    futures = [pool.submit(_run_chunk, graph_dict, chunk, device, snr_db) for chunk in chunks]
                    for future in as_completed(futures):
                        if cancelled and cancelled():
                            was_cancelled = True
                            for pending in futures:
                                pending.cancel()
                            break
                        results.append(future.result())
            for result in results:
                point["bit_errors"] += result["bit_errors"]
                point["total_bits"] += result["total_bits"]
                point["frames"] += result["completed_trials"]
                aggregate["bit_errors"] += result["bit_errors"]
                aggregate["total_bits"] += result["total_bits"]
                aggregate["completed_trials"] += result["completed_trials"]
            offset += len(batch)
            if progress:
                progress({
                    **aggregate,
                    "trials": total_budget,
                    "device": device,
                    "workers": workers,
                    "snr_db": snr_db,
                    "snr_index": snr_index,
                    "snr_count": len(snr_values),
                })
            stop_criteria_met = point["frames"] >= min_frames and (
                point["bit_errors"] >= config.min_errors or point["frames"] >= max_frames
            )
            if was_cancelled or stop_criteria_met:
                break
        point_results.append({
            "snr_db": snr_db,
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
        "device": device,
        "workers": workers,
        "cancelled": was_cancelled,
        "snr_points": point_results,
        "warnings": validation.warnings + (["GPU unavailable or graph incompatible; used CPU"] if config.device == "auto" and device == "cpu" else []),
    }
