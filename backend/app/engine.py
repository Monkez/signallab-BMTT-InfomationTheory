from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .block_registry import SPEC_BY_TYPE
from .blocks import PROCESSORS, make_context, python_block, to_numpy
from .contracts import BlockExecutionError, validate_inputs, validate_outputs, validate_parameters
from .models import Graph, SimulationConfig, ValidationResult
from .python_ports import PythonPortDefinitionError, parse_python_ports
from .variables import VariableDefinitionError, collect_global_variables


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
    node_errors: dict[str, list[str]] = {}
    node_map = {node.id: node for node in graph.nodes}
    node_ports: dict[str, tuple[list[str], list[str]]] = {}

    def block_error(node_id: str, message: str) -> None:
        node = node_map.get(node_id)
        errors.append(f"Block '{node.label if node else node_id}': {message}")
        node_errors.setdefault(node_id, []).append(message)

    if not graph.nodes:
        errors.append("Graph has no blocks")
    variable_nodes = [node for node in graph.nodes if node.type == "variables"]
    if len(variable_nodes) > 1:
        for node in variable_nodes:
            block_error(node.id, "only one Variables block is allowed in a simulation")
    for node in graph.nodes:
        if node.type not in SPEC_BY_TYPE:
            block_error(node.id, f"unknown type '{node.type}'")
            continue
        if node.type == "python":
            try:
                python_ports = parse_python_ports(node.code)
                node_ports[node.id] = (python_ports.inputs, python_ports.outputs)
            except PythonPortDefinitionError as exc:
                block_error(node.id, str(exc))
                node_ports[node.id] = ([], [])
        else:
            spec = SPEC_BY_TYPE[node.type]
            node_ports[node.id] = (spec.inputs, spec.outputs)
        for message in validate_parameters(node.type, node.params):
            block_error(node.id, message)
    incoming: dict[str, set[str]] = {node.id: set() for node in graph.nodes}
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    indegree = {node.id: 0 for node in graph.nodes}
    for edge in graph.edges:
        if edge.source not in node_map or edge.target not in node_map:
            errors.append(f"Edge '{edge.id}' references a missing block")
            continue
        source_ports = node_ports.get(edge.source)
        target_ports = node_ports.get(edge.target)
        if source_ports and edge.source_handle not in source_ports[1]:
            block_error(edge.source, f"edge '{edge.id}' uses unknown output port '{edge.source_handle}'")
            continue
        if target_ports and edge.target_handle not in target_ports[0]:
            block_error(edge.target, f"edge '{edge.id}' uses unknown input port '{edge.target_handle}'")
            continue
        if edge.target_handle in incoming[edge.target]:
            block_error(edge.target, f"input '{edge.target_handle}' has more than one connection")
            continue
        incoming[edge.target].add(edge.target_handle)
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1
    for node in graph.nodes:
        ports = node_ports.get(node.id)
        if ports:
            for port in ports[0]:
                if port not in incoming[node.id]:
                    block_error(node.id, f"missing input '{port}'")
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
        for node_id, degree in indegree.items():
            if degree > 0:
                block_error(node_id, "participates in a cycle")
    if not any(node.type == "ber" for node in graph.nodes):
        warnings.append("Graph has no BER Meter, so no BER metric will be produced")
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings, node_errors=node_errors)


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


def _preview_value(value: Any, sample_limit: int = 8) -> dict[str, Any]:
    """Return a small JSON-safe signal summary; never send full frame buffers to UI."""
    try:
        array = np.asarray(to_numpy(value))
    except Exception:
        return {"dtype": type(value).__name__, "shape": [], "size": 1, "sample": [repr(value)[:120]]}
    flat = array.reshape(-1)

    def format_scalar(item: Any) -> str:
        scalar = item.item() if hasattr(item, "item") else item
        if isinstance(scalar, complex):
            return f"{scalar.real:.5g}{scalar.imag:+.5g}j"
        if isinstance(scalar, float):
            return f"{scalar:.6g}"
        return str(scalar)

    preview: dict[str, Any] = {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "size": int(array.size),
        "sample": [format_scalar(item) for item in flat[:sample_limit]],
    }
    if array.size and np.issubdtype(array.dtype, np.number):
        numeric = np.abs(array) if np.iscomplexobj(array) else array.astype(float, copy=False)
        preview.update({
            "min": float(np.min(numeric)),
            "max": float(np.max(numeric)),
            "mean": float(np.mean(numeric)),
            "stats_label": "|x|" if np.iscomplexobj(array) else "value",
        })
    return preview


def _preview_limit(node_type: str) -> int:
    """Keep ordinary port previews small, but give constellation plots enough points.

    A benchmark may run hundreds of frames, while the UI preview is captured from
    one representative frame. Eight values (the generic limit) makes a noisy I/Q
    cloud look like only a few dots, so the constellation sink gets a bounded,
    plot-friendly sample without sending the full signal buffer to the browser.
    """
    return 2048 if node_type == "constellation" else 8


def _capture_value(value: Any) -> np.ndarray:
    """Keep the representative frame for lazy inspection; move GPU data once."""
    return np.array(to_numpy(value), copy=True)


def execute_trial(
    graph_dict: dict[str, Any],
    trial_index: int,
    seed: int,
    device: str = "cpu",
    snr_db: float | None = None,
    capture_ports: bool = False,
) -> dict[str, Any]:
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
    try:
        global_variables = graph_dict.get("_global_variables")
        if global_variables is None:
            global_variables = collect_global_variables(graph_dict["nodes"])
    except VariableDefinitionError as exc:
        variable_node = next((node for node in graph_dict["nodes"] if node["type"] == "variables"), None)
        raise BlockExecutionError(
            variable_node["id"] if variable_node else "variables",
            variable_node.get("label", "Variables") if variable_node else "Variables",
            str(exc),
        ) from exc
    context = make_context(
        xp,
        rng,
        trial_index,
        seed,
        actual_device,
        snr_db,
        graph_dict.get("_random_seed_root"),
        global_variables,
    )
    nodes = graph_dict.get("_node_map") or {node["id"]: node for node in graph_dict["nodes"]}
    outputs: dict[str, dict[str, Any]] = {}
    port_previews: dict[str, dict[str, dict[str, Any]]] = {}
    port_values: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    metrics: dict[str, float] = {"bit_errors": 0, "total_bits": 0}
    incoming = graph_dict.get("_incoming_edges")
    if incoming is None:
        incoming = {node_id: [] for node_id in nodes}
        for edge in graph_dict["edges"]:
            incoming[edge["target"]].append(edge)
    order = graph_dict.get("_execution_order") or topological_order(graph_dict)
    for node_id in order:
        node = nodes[node_id]
        context.node_id = node_id
        spec = SPEC_BY_TYPE[node["type"]]
        declared_outputs = spec.outputs
        if node["type"] == "python":
            try:
                python_ports = parse_python_ports(node.get("code"))
                declared_outputs = python_ports.outputs
            except PythonPortDefinitionError as exc:
                raise BlockExecutionError(node_id, node.get("label", "Python Block"), str(exc)) from exc
        node_inputs = {}
        for edge in incoming[node_id]:
            node_inputs[edge.get("target_handle", "in")] = outputs[edge["source"]][edge.get("source_handle", "out")]
        if capture_ports:
            captured_inputs = {
                edge.get("target_handle", "in"): port_values[edge["source"]]["outputs"][edge.get("source_handle", "out")]
                for edge in incoming[node_id]
            }
            limit = _preview_limit(node["type"])
            port_previews[node_id] = {
                "inputs": {name: _preview_value(value, sample_limit=limit) for name, value in captured_inputs.items()},
                "outputs": {},
            }
            port_values[node_id] = {
                "inputs": captured_inputs,
                "outputs": {},
            }
        try:
            validate_inputs(node["type"], node_inputs, node.get("params", {}))
            if node["type"] == "python":
                result = python_block(node_inputs, node.get("params", {}), context, node.get("code"))
            else:
                result = PROCESSORS[node["type"]](node_inputs, node.get("params", {}), context)
            if not isinstance(result, dict):
                raise ValueError("processor must return a dictionary of output ports")
            validate_outputs(node["type"], node_inputs, result, declared_outputs, node.get("params", {}))
        except BlockExecutionError:
            raise
        except Exception as exc:
            raise BlockExecutionError(node_id, node.get("label", node["type"]), str(exc)) from exc
        node_metrics = result.pop("__metrics__", None)
        if node_metrics:
            for key, value in node_metrics.items():
                metrics[key] = metrics.get(key, 0) + float(value)
        outputs[node_id] = result
        if capture_ports:
            captured_outputs = {name: _capture_value(value) for name, value in result.items()}
            port_values[node_id]["outputs"] = captured_outputs
            limit = _preview_limit(node["type"])
            port_previews[node_id]["outputs"] = {name: _preview_value(value, sample_limit=limit) for name, value in captured_outputs.items()}
    return {"metrics": metrics, "port_previews": port_previews, "_port_values": port_values} if capture_ports else metrics


def _execution_device(graph: Graph, requested: str) -> tuple[str, list[str]]:
    gpu = gpu_status()
    gpu_compatible = all(SPEC_BY_TYPE[node.type].gpu_compatible for node in graph.nodes)
    if requested == "gpu" and not gpu["available"]:
        raise ValueError("GPU was requested but CuPy/CUDA is unavailable")
    device = "gpu" if requested in ("gpu", "auto") and gpu["available"] and gpu_compatible else "cpu"
    warnings = ["GPU unavailable or graph incompatible; used CPU"] if requested == "auto" and device == "cpu" else []
    return device, warnings


def run_once(graph: Graph, config: SimulationConfig) -> dict[str, Any]:
    validation = validate_graph(graph)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    started = time.perf_counter()
    device, device_warnings = _execution_device(graph, config.device)
    graph_dict = graph.model_dump()
    graph_dict["_global_variables"] = collect_global_variables(graph_dict["nodes"])
    graph_dict["_random_seed_root"] = int.from_bytes(os.urandom(8), "little")
    snr_db = None if config.mode == "specific_steps" else float(config.snr_db_start)
    captured = execute_trial(graph_dict, 0, config.seed, device, snr_db, capture_ports=True)
    return {
        "device": device,
        "snr_db": snr_db,
        "elapsed_seconds": time.perf_counter() - started,
        "metrics": captured["metrics"],
        "sink_metrics": _sink_metrics(captured["metrics"]),
        "port_previews": captured["port_previews"],
        "_port_values": captured["_port_values"],
        "warnings": validation.warnings + device_warnings,
    }


def _run_chunk(
    graph_dict: dict[str, Any],
    items: list[tuple[int, int]],
    device: str,
    snr_db: float | None,
) -> dict[str, float]:
    total: dict[str, float] = {"completed_trials": 0}
    for trial_index, seed in items:
        result = execute_trial(graph_dict, trial_index, seed, device, snr_db)
        for key, value in result.items():
            total[key] = total.get(key, 0) + value
        total["completed_trials"] += 1
    return total


def _merge_metrics(target: dict[str, float], source: dict[str, float]) -> None:
    for key, value in source.items():
        if key == "completed_trials":
            target[key] = target.get(key, 0) + value
        elif key.endswith("_peak"):
            target[key] = max(target.get(key, 0), value)
        else:
            target[key] = target.get(key, 0) + value


def _sink_metrics(aggregate: dict[str, float]) -> dict[str, float]:
    """Convert raw per-frame sink counters into presentation-ready metrics."""
    sink_metrics: dict[str, float] = {}
    if aggregate.get("power_count", 0):
        sink_metrics["power_mean"] = aggregate.get("power_sum", 0) / aggregate["power_count"]
    if aggregate.get("scope_count", 0):
        sink_metrics["scope_mean_amplitude"] = aggregate.get("scope_sum", 0) / aggregate["scope_count"]
        sink_metrics["scope_peak_amplitude"] = aggregate.get("scope_peak", 0)
    if aggregate.get("constellation_count", 0):
        count = aggregate["constellation_count"]
        sink_metrics["constellation_mean_i"] = aggregate.get("constellation_i_sum", 0) / count
        sink_metrics["constellation_mean_q"] = aggregate.get("constellation_q_sum", 0) / count
        sink_metrics["constellation_mean_power"] = aggregate.get("constellation_power_sum", 0) / count
    if aggregate.get("source_frame_count", 0):
        frames = aggregate["source_frame_count"]
        symbols = aggregate.get("source_symbol_count", 0)
        sink_metrics["source_entropy"] = aggregate.get("source_entropy_sum", 0) / frames
        sink_metrics["source_max_entropy"] = aggregate.get("source_max_entropy_sum", 0) / frames
        sink_metrics["source_efficiency_percent"] = aggregate.get("source_efficiency_sum", 0) / frames
        sink_metrics["source_average_information"] = aggregate.get("source_information_sum", 0) / symbols if symbols else 0
        sink_metrics["source_alphabet_size"] = aggregate.get("source_alphabet_size_peak", 0)
    if aggregate.get("total_symbols", 0):
        sink_metrics["symbol_errors"] = aggregate.get("symbol_errors", 0)
        sink_metrics["total_symbols"] = aggregate["total_symbols"]
        sink_metrics["ser"] = aggregate.get("symbol_errors", 0) / aggregate["total_symbols"]
    return sink_metrics


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
    graph_dict["_global_variables"] = collect_global_variables(graph_dict["nodes"])
    graph_dict["_random_seed_root"] = int.from_bytes(os.urandom(8), "little")
    # Compile immutable graph lookups once. They are plain dictionaries/lists,
    # so the compiled plan is also serializable to ProcessPool workers.
    graph_dict["_node_map"] = {node["id"]: node for node in graph_dict["nodes"]}
    graph_dict["_incoming_edges"] = {node["id"]: [] for node in graph_dict["nodes"]}
    for edge in graph_dict["edges"]:
        graph_dict["_incoming_edges"][edge["target"]].append(edge)
    graph_dict["_execution_order"] = topological_order(graph_dict)
    max_frames = config.max_frames or config.trials
    min_frames = min(config.min_frames, max_frames)
    if config.mode == "specific_steps":
        # A specific-step experiment is deliberately SNR-neutral: run a fixed
        # number of frames once and let channels use their own block defaults.
        snr_values = [None]
    else:
        if config.snr_db_stop < config.snr_db_start:
            raise ValueError("SNR stop must be greater than or equal to SNR start")
        snr_values = [
            round(float(value), 6)
            for value in np.arange(config.snr_db_start, config.snr_db_stop + config.snr_db_step * 0.5, config.snr_db_step)
        ]
        if not snr_values:
            snr_values = [round(float(config.snr_db_start), 6)]
    device, device_warnings = _execution_device(graph, config.device)
    cpu_count = os.cpu_count() or 1
    # Auto mode avoids creating one OS process per frame on high-core machines
    # and keeps small vectorized jobs inline, where ProcessPool overhead wins.
    if config.workers:
        workers = config.workers
    else:
        workers = 1 if max_frames < 128 else min(32, max(1, cpu_count - 1), max_frames // max(1, config.chunk_size))
    workers = min(workers, max_frames, cpu_count)
    if device == "gpu":
        workers = 1
    aggregate: dict[str, float] = {"bit_errors": 0, "total_bits": 0, "completed_trials": 0}
    point_results: list[dict[str, Any]] = []
    total_budget = len(snr_values) * max_frames
    was_cancelled = False
    pool = (
        ProcessPoolExecutor(max_workers=workers)
        if device == "cpu" and workers > 1 and max_frames >= max(4, config.chunk_size)
        else None
    )

    try:
        for snr_index, snr_db in enumerate(snr_values):
            point: dict[str, float] = {"bit_errors": 0, "total_bits": 0, "frames": 0}
            seed_rng = np.random.default_rng(np.random.SeedSequence([config.seed, snr_index]))
            offset = 0
            while offset < max_frames:
                if cancelled and cancelled():
                    was_cancelled = True
                    break
                batch_size = min(config.chunk_size * workers, max_frames - offset)
                batch_seeds = seed_rng.integers(0, np.iinfo(np.uint32).max, size=batch_size, dtype=np.uint32)
                batch = [(offset + index, int(seed)) for index, seed in enumerate(batch_seeds)]
                chunks = [batch[i : i + config.chunk_size] for i in range(0, len(batch), config.chunk_size)]
                results: list[dict[str, float]] = []
                if workers == 1 or len(batch) < max(4, config.chunk_size):
                    results = [_run_chunk(graph_dict, chunk, device, snr_db) for chunk in chunks]
                elif pool is not None:
                    futures = [pool.submit(_run_chunk, graph_dict, chunk, device, snr_db) for chunk in chunks]
                    for future in as_completed(futures):
                        if cancelled and cancelled():
                            was_cancelled = True
                            for pending in futures:
                                pending.cancel()
                            break
                        results.append(future.result())
                for result in results:
                    _merge_metrics(point, result)
                    _merge_metrics(aggregate, result)
                    point["frames"] += result.get("completed_trials", 0)
                offset += len(batch)
                if progress:
                    live_points = [*point_results, {
                        "snr_db": snr_db,
                        "bit_errors": point["bit_errors"],
                        "total_bits": point["total_bits"],
                        "frames": point["frames"],
                        "ber": point["bit_errors"] / point["total_bits"] if point["total_bits"] else None,
                    }]
                    progress({
                        **aggregate,
                        "trials": total_budget,
                        "device": device,
                        "workers": workers,
                        "snr_db": snr_db,
                        "snr_index": snr_index,
                        "snr_count": len(snr_values),
                        "snr_points": live_points,
                    })
                stop_criteria_met = point["frames"] >= max_frames
                if config.mode == "ber_benchmark":
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
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
    elapsed = time.perf_counter() - started
    bits = aggregate["total_bits"]
    sink_metrics: dict[str, float] = {}
    if aggregate.get("power_count", 0):
        sink_metrics["power_mean"] = aggregate.get("power_sum", 0) / aggregate["power_count"]
    if aggregate.get("scope_count", 0):
        sink_metrics["scope_mean_amplitude"] = aggregate.get("scope_sum", 0) / aggregate["scope_count"]
        sink_metrics["scope_peak_amplitude"] = aggregate.get("scope_peak", 0)
    if aggregate.get("constellation_count", 0):
        count = aggregate["constellation_count"]
        sink_metrics["constellation_mean_i"] = aggregate.get("constellation_i_sum", 0) / count
        sink_metrics["constellation_mean_q"] = aggregate.get("constellation_q_sum", 0) / count
        sink_metrics["constellation_mean_power"] = aggregate.get("constellation_power_sum", 0) / count
    if aggregate.get("source_frame_count", 0):
        frames = aggregate["source_frame_count"]
        symbols = aggregate.get("source_symbol_count", 0)
        sink_metrics["source_entropy"] = aggregate.get("source_entropy_sum", 0) / frames
        sink_metrics["source_max_entropy"] = aggregate.get("source_max_entropy_sum", 0) / frames
        sink_metrics["source_efficiency_percent"] = aggregate.get("source_efficiency_sum", 0) / frames
        sink_metrics["source_average_information"] = aggregate.get("source_information_sum", 0) / symbols if symbols else 0
        sink_metrics["source_alphabet_size"] = aggregate.get("source_alphabet_size_peak", 0)
    if aggregate.get("total_symbols", 0):
        sink_metrics["symbol_errors"] = aggregate.get("symbol_errors", 0)
        sink_metrics["total_symbols"] = aggregate["total_symbols"]
        sink_metrics["ser"] = aggregate.get("symbol_errors", 0) / aggregate["total_symbols"]
    preview_capture = execute_trial(graph_dict, 0, config.seed, device, snr_values[0], capture_ports=True) if not was_cancelled else {"port_previews": {}, "_port_values": {}}
    return {
        **aggregate,
        "ber": aggregate["bit_errors"] / bits if bits else None,
        "elapsed_seconds": elapsed,
        "throughput_bps": bits / elapsed if elapsed else 0,
        "device": device,
        "workers": workers,
        "cancelled": was_cancelled,
        "snr_points": point_results,
        "sink_metrics": sink_metrics,
        "port_previews": preview_capture["port_previews"],
        "_port_values": preview_capture["_port_values"],
        "warnings": validation.warnings + device_warnings,
    }
