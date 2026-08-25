import base64
import math

import pytest
from fastapi.testclient import TestClient

from backend.app.blocks import PROCESSORS, _stable_huffman_codes, make_context, python_block, python_block_batch, python_has_batch
from backend.app.block_registry import SPEC_BY_TYPE
from backend.app.contracts import BlockExecutionError
from backend.app.contracts import validate_inputs, validate_outputs, validate_parameters
from backend.app.engine import execute_trial, run_once, run_simulation, validate_graph
from backend.app.models import Edge, Graph, SimulationConfig
from backend.app.main import app
from backend.app.native_engine import compile_native_plan, native_status
from backend.app.variables import VariableDefinitionError, parse_variable_definitions
from backend.app.python_ports import PythonPortDefinitionError, parse_python_ports
import numpy as np


NATIVE_AVAILABLE = bool(native_status().get("available"))


def sample_graph():
    node_types = ["bit_source", "hamming74_encode", "bpsk_mod", "awgn", "bpsk_demod", "hamming74_decode", "ber"]
    nodes = [{"id": str(i), "type": kind, "label": kind, "params": {"length": 400, "ebn0_db": 20, "seed": 123}} for i, kind in enumerate(node_types)]
    edges = [
        {"id": "e01", "source": "0", "target": "1", "source_handle": "out", "target_handle": "in"},
        {"id": "e12", "source": "1", "target": "2", "source_handle": "out", "target_handle": "in"},
        {"id": "e23", "source": "2", "target": "3", "source_handle": "out", "target_handle": "in"},
        {"id": "e34", "source": "3", "target": "4", "source_handle": "out", "target_handle": "in"},
        {"id": "e45", "source": "4", "target": "5", "source_handle": "out", "target_handle": "in"},
        {"id": "eref", "source": "1", "target": "6", "source_handle": "reference", "target_handle": "reference"},
        {"id": "e56", "source": "5", "target": "6", "source_handle": "out", "target_handle": "estimate"},
    ]
    return Graph(nodes=nodes, edges=edges)


def uncoded_modulation_graph(modulation: str, length: int = 4096) -> Graph:
    modulator, demodulator = {
        "bpsk": ("bpsk_mod", "bpsk_demod"),
        "qpsk": ("qpsk_mod", "qpsk_demod"),
        "qam16": ("qam16_mod", "qam16_demod"),
    }[modulation]
    return Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": length, "seed": 123}},
        {"id": "mod", "type": modulator, "label": modulator, "params": {}},
        {"id": "channel", "type": "awgn", "label": "AWGN", "params": {"ebn0_db": 4, "snr_mode": "experiment", "seed": 456}},
        {"id": "demod", "type": demodulator, "label": demodulator, "params": {}},
        {"id": "meter", "type": "ber", "label": "BER", "params": {}},
    ], edges=[
        {"id": "source-mod", "source": "source", "target": "mod", "source_handle": "out", "target_handle": "in"},
        {"id": "mod-channel", "source": "mod", "target": "channel", "source_handle": "out", "target_handle": "in"},
        {"id": "channel-demod", "source": "channel", "target": "demod", "source_handle": "out", "target_handle": "in"},
        {"id": "reference", "source": "source", "target": "meter", "source_handle": "out", "target_handle": "reference"},
        {"id": "estimate", "source": "demod", "target": "meter", "source_handle": "out", "target_handle": "estimate"},
    ])


def test_graph_is_valid_and_high_snr_has_no_errors():
    graph = sample_graph()
    assert validate_graph(graph).valid
    result = execute_trial(graph.model_dump(), 0, 42)
    assert result["total_bits"] == 400
    assert result["bit_errors"] == 0


def test_simulation_is_reproducible():
    graph = sample_graph()
    graph.nodes[3].params["ebn0_db"] = 0
    config = SimulationConfig(
        mode="ber_benchmark",
        trials=4,
        max_frames=4,
        min_frames=1,
        min_errors=0,
        snr_db_start=0,
        snr_db_stop=4,
        snr_db_step=2,
        workers=1,
        seed=123,
        chunk_size=2,
        device="cpu",
        engine="python",
    )
    updates = []
    first = run_simulation(graph, config, progress=updates.append)
    second = run_simulation(graph, config)
    assert first["bit_errors"] == second["bit_errors"]
    assert first["total_bits"] == second["total_bits"]
    assert [point["snr_db"] for point in first["snr_points"]] == [0.0, 2.0, 4.0]
    assert updates and updates[-1]["snr_points"][-1]["frames"] >= 1
    assert first["port_previews"]["0"]["outputs"]["out"]["shape"] == [400]


def test_specific_steps_mode_runs_exact_points_with_fixed_frames():
    config = SimulationConfig(
        mode="specific_steps",
        max_frames=2,
        min_frames=1,
        min_errors=999999,
        snr_db_start=3,
        workers=1,
        seed=7,
        chunk_size=1,
        device="cpu",
    )
    result = run_simulation(sample_graph(), config)
    assert [point["snr_db"] for point in result["snr_points"]] == [3.0]
    assert all(point["frames"] == 2 for point in result["snr_points"])


def test_run_once_captures_input_and_output_port_samples():
    result = run_once(sample_graph(), SimulationConfig(seed=42, device="cpu"))
    source = result["port_previews"]["0"]["outputs"]["out"]
    decoder_input = result["port_previews"]["5"]["inputs"]["in"]
    assert source["dtype"] == "int8"
    assert source["shape"] == [400]
    assert len(source["sample"]) == 8
    assert decoder_input["size"] == 700
    assert result["_port_values"]["1"]["inputs"]["in"] is result["_port_values"]["0"]["outputs"]["out"]


def test_run_once_returns_presentation_metrics_for_power_and_constellation_sinks():
    graph = Graph(nodes=[
        {"id": "src", "type": "bit_source", "label": "Bits", "params": {"length": 8, "seed": 1}},
        {"id": "mod", "type": "bpsk_mod", "label": "BPSK", "params": {}},
        {"id": "power", "type": "power_meter", "label": "TX Power", "params": {}},
        {"id": "const", "type": "constellation", "label": "Constellation", "params": {}},
    ], edges=[
        {"id": "e1", "source": "src", "target": "mod"},
        {"id": "e2", "source": "mod", "target": "power"},
        {"id": "e3", "source": "mod", "target": "const"},
    ])
    result = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    assert result["sink_metrics"]["power_mean"] == pytest.approx(1.0)
    assert "constellation_mean_i" in result["sink_metrics"]
    assert result["port_previews"]["const"]["inputs"]["in"]["size"] == 8


def test_awgn_adds_noise_on_both_i_and_q_for_complex_signals():
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu", 4.0)
    clean = np.ones(4096, dtype=np.complex64)
    noisy = PROCESSORS["awgn"]({"in": clean}, {"ebn0_db": 4, "snr_mode": "fixed"}, context)["out"]
    assert np.std(np.real(noisy)) > 0
    assert np.std(np.imag(noisy)) > 0


def test_constellation_preview_keeps_a_plot_sized_sample():
    graph = Graph(nodes=[
        {"id": "src", "type": "bit_source", "label": "Bits", "params": {"length": 4096, "seed": 1}},
        {"id": "mod", "type": "bpsk_mod", "label": "BPSK", "params": {}},
        {"id": "const", "type": "constellation", "label": "Constellation", "params": {}},
    ], edges=[
        {"id": "e1", "source": "src", "target": "mod"},
        {"id": "e2", "source": "mod", "target": "const"},
    ])
    result = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    preview = result["port_previews"]["const"]["inputs"]["in"]
    assert preview["size"] == 4096
    assert len(preview["sample"]) == 2048


def test_run_once_snapshot_exposes_every_port_value_by_page():
    client = TestClient(app)
    response = client.post("/api/run-once", json={
        "graph": sample_graph().model_dump(),
        "config": SimulationConfig(seed=42, device="cpu").model_dump(),
    })
    assert response.status_code == 200
    result = response.json()
    assert "_port_values" not in result
    page = client.get(f"/api/snapshots/{result['snapshot_id']}/nodes/0/ports/outputs/out?offset=396&limit=16")
    assert page.status_code == 200
    payload = page.json()
    assert payload["total"] == 400
    assert payload["offset"] == 396
    assert len(payload["values"]) == 4


def test_random_block_seed_defaults_and_validation():
    for block_type in ("bit_source", "awgn", "rayleigh"):
        assert SPEC_BY_TYPE[block_type].defaults["seed"] == -1
        assert validate_parameters(block_type, {**SPEC_BY_TYPE[block_type].defaults, "seed": -2})
        assert not validate_parameters(block_type, {**SPEC_BY_TYPE[block_type].defaults, "seed": 0})


@pytest.mark.parametrize(("block_type", "inputs", "extra_params"), [
    ("bit_source", {}, {"length": 256}),
    ("awgn", {"in": np.ones(256, dtype=np.float32)}, {"ebn0_db": 4, "snr_mode": "fixed"}),
    ("rayleigh", {"in": np.ones(256, dtype=np.float32)}, {"ebn0_db": 4, "snr_mode": "fixed"}),
])
def test_random_blocks_support_random_and_reproducible_seeds(block_type, inputs, extra_params):
    def output(block_seed: int, root: int, trial_seed: int = 77):
        context = make_context(np, np.random.default_rng(trial_seed), 0, trial_seed, "cpu", 4.0, root)
        context.node_id = f"test-{block_type}"
        return np.asarray(PROCESSORS[block_type](inputs, {**extra_params, "seed": block_seed}, context)["out"])

    assert np.array_equal(output(2026, 11), output(2026, 99))
    assert not np.array_equal(output(2026, 11, 77), output(2026, 11, 78))
    assert not np.array_equal(output(-1, 11), output(-1, 99))


def test_run_once_random_seed_changes_and_fixed_seed_repeats_port_data():
    graph = sample_graph()
    graph.nodes[0].params["seed"] = -1
    graph.nodes[3].params["seed"] = -1
    first_random = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    second_random = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    assert not np.array_equal(first_random["_port_values"]["0"]["outputs"]["out"], second_random["_port_values"]["0"]["outputs"]["out"])
    assert not np.array_equal(first_random["_port_values"]["3"]["outputs"]["out"], second_random["_port_values"]["3"]["outputs"]["out"])

    graph.nodes[0].params["seed"] = 1001
    graph.nodes[3].params["seed"] = 2002
    first_fixed = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    second_fixed = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    assert np.array_equal(first_fixed["_port_values"]["0"]["outputs"]["out"], second_fixed["_port_values"]["0"]["outputs"]["out"])
    assert np.array_equal(first_fixed["_port_values"]["3"]["outputs"]["out"], second_fixed["_port_values"]["3"]["outputs"]["out"])


def test_hamming_rejects_input_that_would_be_silently_padded():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 402
    with pytest.raises(BlockExecutionError) as captured:
        run_once(graph, SimulationConfig(seed=42, device="cpu"))
    assert captured.value.node_id == "1"
    assert "multiple of 4" in captured.value.reason

    with pytest.raises(BlockExecutionError) as parallel_capture:
        run_simulation(graph, SimulationConfig(max_frames=4, min_frames=1, min_errors=0, snr_db_start=0, snr_db_stop=0, workers=2, chunk_size=2, device="cpu"))
    assert parallel_capture.value.node_id == "1"


def test_hamming_uses_systematic_data_then_parity_layout():
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu")
    data = np.array([1, 1, 0, 1], dtype=np.int8)
    encoded = PROCESSORS["hamming74_encode"]({"in": data}, {}, context)["out"]

    assert encoded.tolist() == [1, 1, 0, 1, 1, 0, 0]
    assert encoded[:4].tolist() == data.tolist()
    assert PROCESSORS["hamming74_decode"]({"in": encoded}, {}, context)["out"].tolist() == data.tolist()


def test_hamming_corrects_every_single_bit_error_for_all_messages():
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu")
    for value in range(16):
        data = np.array([(value >> shift) & 1 for shift in (3, 2, 1, 0)], dtype=np.int8)
        encoded = PROCESSORS["hamming74_encode"]({"in": data}, {}, context)["out"]
        for error_index in range(7):
            corrupted = encoded.copy()
            corrupted[error_index] ^= 1
            decoded = PROCESSORS["hamming74_decode"]({"in": corrupted}, {}, context)["out"]
            assert np.array_equal(decoded, data), (value, error_index)


def test_ber_requires_reference_and_estimate_to_match_exactly():
    graph = Graph(nodes=[
        {"id": "reference", "type": "bit_source", "label": "Reference", "params": {"length": 8}},
        {"id": "estimate", "type": "bit_source", "label": "Estimate", "params": {"length": 7}},
        {"id": "meter", "type": "ber", "label": "BER meter", "params": {}},
    ], edges=[
        {"id": "ref", "source": "reference", "target": "meter", "source_handle": "out", "target_handle": "reference"},
        {"id": "est", "source": "estimate", "target": "meter", "source_handle": "out", "target_handle": "estimate"},
    ])
    with pytest.raises(BlockExecutionError) as captured:
        execute_trial(graph.model_dump(), 0, 42)
    assert captured.value.node_id == "meter"
    assert "reference has 8 values, estimate has 7" in captured.value.reason


def test_python_block_defaults_to_same_input_and_output_size():
    graph = Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Source", "params": {"length": 8}},
        {"id": "custom", "type": "python", "label": "Custom", "params": {"output_size": "same"}, "code": "def process(signal, params):\n    return signal[:-1]"},
    ], edges=[{"id": "edge", "source": "source", "target": "custom"}])
    with pytest.raises(BlockExecutionError) as captured:
        execute_trial(graph.model_dump(), 0, 42)
    assert captured.value.node_id == "custom"
    assert "expected 8, received 7" in captured.value.reason


def test_static_validation_marks_duplicate_input_connection():
    graph = sample_graph()
    graph.edges.append(Edge(id="duplicate", source="0", target="1", target_handle="in"))
    validation = validate_graph(graph)
    assert not validation.valid
    assert "1" in validation.node_errors
    assert "more than one connection" in validation.node_errors["1"][0]


@pytest.mark.parametrize(("block_type", "signal", "expected_size"), [
    ("differential_encode", np.array([0, 1, 1, 0], dtype=np.int8), 4),
    ("differential_decode", np.array([0, 1, 0, 0], dtype=np.int8), 4),
    ("hamming74_encode", np.zeros(8, dtype=np.int8), 14),
    ("hamming74_decode", np.zeros(14, dtype=np.int8), 8),
    ("repetition3_encode", np.zeros(4, dtype=np.int8), 12),
    ("repetition3_decode", np.zeros(12, dtype=np.int8), 4),
    ("bpsk_mod", np.zeros(8, dtype=np.int8), 8),
    ("qpsk_mod", np.zeros(8, dtype=np.int8), 4),
    ("ook_mod", np.zeros(8, dtype=np.int8), 8),
    ("psk8_mod", np.zeros(12, dtype=np.int8), 4),
    ("qam16_mod", np.zeros(16, dtype=np.int8), 4),
    ("awgn", np.ones(8, dtype=np.float32), 8),
    ("rayleigh", np.ones(8, dtype=np.float32), 8),
    ("bpsk_demod", np.ones(8, dtype=np.float32), 8),
    ("qpsk_demod", np.ones(4, dtype=np.complex64), 8),
    ("ook_demod", np.ones(8, dtype=np.float32), 8),
    ("psk8_demod", np.ones(4, dtype=np.complex64), 12),
    ("qam16_demod", np.ones(4, dtype=np.complex64), 16),
])
def test_builtin_signal_processors_obey_declared_size_contract(block_type, signal, expected_size):
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu", 4.0)
    inputs = {"in": signal}
    validate_inputs(block_type, inputs, {})
    outputs = PROCESSORS[block_type](inputs, {}, context)
    validate_outputs(block_type, inputs, outputs, SPEC_BY_TYPE[block_type].outputs, {})
    assert outputs["out"].size == expected_size


@pytest.mark.parametrize(("modulator", "demodulator", "bits"), [
    ("ook_mod", "ook_demod", np.asarray([0, 1, 1, 0, 1, 0], dtype=np.int8)),
    ("psk8_mod", "psk8_demod", np.asarray(list(np.ndindex((2, 2, 2))), dtype=np.int8).reshape(-1)),
    ("qam16_mod", "qam16_demod", np.asarray(list(np.ndindex((2, 2, 2, 2))), dtype=np.int8).reshape(-1)),
])
def test_additional_modulation_blocks_round_trip_without_noise(modulator, demodulator, bits):
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu", 20.0)
    symbols = PROCESSORS[modulator]({"in": bits}, {}, context)["out"]
    recovered = PROCESSORS[demodulator]({"in": symbols}, {}, context)["out"]
    assert np.array_equal(recovered, bits)


def test_cycle_is_rejected():
    graph = sample_graph()
    graph.edges.append(Edge(id="cycle", source="5", target="2"))
    assert not validate_graph(graph).valid


def test_qpsk_graph_reports_sink_metrics():
    nodes = [
        {"id": "src", "type": "text_source", "label": "Text", "params": {"text": "AB", "repeat": 1}},
        {"id": "mod", "type": "qpsk_mod", "label": "QPSK", "params": {}},
        {"id": "channel", "type": "awgn", "label": "AWGN", "params": {"snr_mode": "experiment"}},
        {"id": "demod", "type": "qpsk_demod", "label": "QPSK Demod", "params": {}},
        {"id": "ber", "type": "ber", "label": "BER", "params": {}},
        {"id": "power", "type": "power_meter", "label": "Power", "params": {}},
    ]
    edges = [
        {"id": "e1", "source": "src", "target": "mod", "source_handle": "out", "target_handle": "in"},
        {"id": "e2", "source": "mod", "target": "channel", "source_handle": "out", "target_handle": "in"},
        {"id": "e3", "source": "channel", "target": "demod", "source_handle": "out", "target_handle": "in"},
        {"id": "e4", "source": "demod", "target": "ber", "source_handle": "out", "target_handle": "estimate"},
        {"id": "e5", "source": "src", "target": "ber", "source_handle": "reference", "target_handle": "reference"},
        {"id": "e6", "source": "channel", "target": "power", "source_handle": "out", "target_handle": "in"},
    ]
    graph = Graph(nodes=nodes, edges=edges)
    result = run_simulation(graph, SimulationConfig(max_frames=2, min_frames=1, min_errors=0, snr_db_start=0, snr_db_stop=0, workers=1, chunk_size=1, device="cpu"))
    assert result["sink_metrics"]["power_mean"] > 0


def test_python_block_supports_natural_and_legacy_apis():
    context = make_context(np, np.random.default_rng(1), 0, 1, "cpu")
    signal = np.array([1.0, 2.0])
    natural = "def process(signal, params):\n    return signal * params['gain']"
    assert (python_block({"in": signal}, {"gain": 3}, context, natural)["out"] == [3.0, 6.0]).all()
    legacy = "def process(inputs, params, context):\n    return {'out': inputs['in'] + 1}"
    assert (python_block({"in": signal}, {}, context, legacy)["out"] == [2.0, 3.0]).all()


def test_python_block_batch_vectorizes_frames_and_runtime_params():
    code = """def process(signal, params):
    return np.asarray(signal) * params["gain"]

def process_batch(signals, params_batch):
    gains = np.asarray([params["gain"] + params["trial_index"] for params in params_batch])[:, None]
    return np.asarray(signals) * gains
"""
    contexts = [make_context(np, np.random.default_rng(index), index, 100 + index, "cpu") for index in range(3)]
    results = python_block_batch(
        [{"in": np.asarray([1.0, 2.0])} for _ in contexts],
        {"gain": 2.0},
        contexts,
        code,
    )
    assert python_has_batch(code)
    assert [result["out"].tolist() for result in results] == [[2.0, 4.0], [3.0, 6.0], [4.0, 8.0]]


def test_python_block_batch_supports_named_multiple_outputs():
    code = """PORTS = {"inputs": ["left", "right"], "outputs": ["sum", "difference"]}
def process_batch(inputs, params_batch):
    return {"sum": inputs["left"] + inputs["right"], "difference": inputs["left"] - inputs["right"]}
"""
    contexts = [make_context(np, np.random.default_rng(index), index, index, "cpu") for index in range(2)]
    results = python_block_batch(
        [
            {"left": np.asarray([1, 2]), "right": np.asarray([3, 4])},
            {"left": np.asarray([5, 6]), "right": np.asarray([1, 2])},
        ],
        {},
        contexts,
        code,
    )
    assert results[0]["sum"].tolist() == [4, 6]
    assert results[1]["difference"].tolist() == [4, 4]


def test_simulation_scheduler_uses_python_batch_path_without_changing_preview_api():
    code = """def process(signal, params):
    if params["trial_index"] != 0:
        raise AssertionError("frame API should only be used for the representative preview")
    return (np.asarray(signal) < 0).astype(np.int8)

def process_batch(signals, params_batch):
    return (np.asarray(signals) < 0).astype(np.int8)
"""
    graph = Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": 128, "seed": 7}},
        {"id": "mod", "type": "bpsk_mod", "label": "BPSK", "params": {}},
        {"id": "custom", "type": "python", "label": "Batch detector", "params": {"output_size": "same"}, "code": code},
        {"id": "meter", "type": "ber", "label": "BER", "params": {}},
    ], edges=[
        {"id": "e1", "source": "source", "target": "mod"},
        {"id": "e2", "source": "mod", "target": "custom"},
        {"id": "e3", "source": "source", "target": "meter", "target_handle": "reference"},
        {"id": "e4", "source": "custom", "target": "meter", "target_handle": "estimate"},
    ])
    result = run_simulation(graph, SimulationConfig(
        mode="specific_steps",
        max_frames=8,
        min_frames=8,
        workers=1,
        chunk_size=8,
        device="cpu",
        engine="python",
    ))
    assert result["bit_errors"] == 0
    assert result["execution"]["python_batch_blocks"] == 1
    assert result["port_previews"]["custom"]["outputs"]["out"]["size"] == 128


def test_python_block_can_force_persistent_process_executor_for_small_frames():
    graph = Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": 64, "seed": 7}},
        {"id": "custom", "type": "python", "label": "CPU-heavy custom", "params": {"output_size": "same", "runtime_executor": "process", "runtime_batch_size": 0}, "code": "def process(signal, params):\n    return np.asarray(signal)\n"},
        {"id": "sink", "type": "power_meter", "label": "Power", "params": {}},
    ], edges=[
        {"id": "e1", "source": "source", "target": "custom"},
        {"id": "e2", "source": "custom", "target": "sink"},
    ])
    result = run_simulation(graph, SimulationConfig(
        mode="specific_steps",
        max_frames=16,
        min_frames=16,
        workers=0,
        chunk_size=4,
        device="cpu",
        engine="python",
    ))
    assert result["execution"]["scheduler"] == "persistent_process_pool"
    assert result["execution"]["executor_hint"] == "process"
    assert result["workers"] > 1


def test_python_source_can_use_process_params_and_reports_missing_keys_clearly():
    context = make_context(np, np.random.default_rng(1), 0, 1, "cpu")
    source = 'PORTS = {"inputs": [], "outputs": ["out"]}\ndef process(params):\n    return np.zeros(params["length"], dtype=np.int8)'
    result = python_block({}, {"length": 5}, context, source)
    assert result["out"].size == 5
    broken = 'PORTS = {"inputs": [], "outputs": ["out"]}\ndef process(params):\n    return np.zeros(params["missing"], dtype=np.int8)'
    with pytest.raises(ValueError, match=r"line 3.*missing key 'missing'.*Available params: .*length"):
        python_block({}, {"length": 5}, context, broken)


def test_variables_parser_accepts_typed_literals_and_rejects_executable_code():
    parsed = parse_variable_definitions("""
# Course parameters
symbol_rate = 1_000_000
rolloff = 0.35
enabled = True
label = 'Lab A'
taps = [1.0, 0.5, 0.25]
metadata = {'unit': 'baud'}
""")
    assert parsed == {
        "symbol_rate": 1_000_000,
        "rolloff": 0.35,
        "enabled": True,
        "label": "Lab A",
        "taps": [1.0, 0.5, 0.25],
        "metadata": {"unit": "baud"},
    }
    with pytest.raises(VariableDefinitionError, match="literal value"):
        parse_variable_definitions("danger = __import__('os').getcwd()")
    with pytest.raises(VariableDefinitionError, match="reserved"):
        parse_variable_definitions("snr_db = 10")


def test_python_block_receives_current_experiment_step_and_global_variables():
    code = """def process(signal, params):
    assert params['snr_db'] == 6.5
    assert params['trial_index'] == 3
    assert params['frame_seed'] == 42
    assert params['device'] == 'cpu'
    assert params['experiment']['snr_db'] == 6.5
    assert params['experiment']['trial_index'] == 3
    assert params['symbol_rate'] == 1_000_000
    assert params['variables']['rolloff'] == 0.35
    return signal
"""
    graph = Graph(nodes=[
        {"id": "globals", "type": "variables", "label": "Variables", "params": {"definitions": "symbol_rate = 1_000_000\nrolloff = 0.35"}},
        {"id": "source", "type": "bit_source", "label": "Source", "params": {"length": 8, "seed": 1}},
        {"id": "custom", "type": "python", "label": "Custom", "params": {"output_size": "same"}, "code": code},
    ], edges=[{"id": "edge", "source": "source", "target": "custom"}])
    assert validate_graph(graph).valid
    result = execute_trial(graph.model_dump(), trial_index=3, seed=42, snr_db=6.5, capture_ports=True)
    assert result["port_previews"]["custom"]["outputs"]["out"]["size"] == 8


def test_python_block_supports_named_multiple_inputs_and_outputs_declared_in_code():
    code = """PORTS = {"inputs": ["signal", "noise"], "outputs": ["out", "residual"]}
def process(inputs, params):
    signal = np.asarray(inputs["signal"])
    noise = np.asarray(inputs["noise"])
    return {"out": signal + noise, "residual": signal - noise}
"""
    graph = Graph(nodes=[
        {"id": "signal", "type": "bit_source", "label": "Signal", "params": {"length": 8, "seed": 1}},
        {"id": "noise", "type": "bit_source", "label": "Noise", "params": {"length": 8, "seed": 2}},
        {"id": "custom", "type": "python", "label": "Two-input Python", "params": {"output_size": "same"}, "code": code},
    ], edges=[
        {"id": "signal-in", "source": "signal", "target": "custom", "source_handle": "out", "target_handle": "signal"},
        {"id": "noise-in", "source": "noise", "target": "custom", "source_handle": "out", "target_handle": "noise"},
    ])
    assert parse_python_ports(code).inputs == ["signal", "noise"]
    assert parse_python_ports(code).outputs == ["out", "residual"]
    assert validate_graph(graph).valid
    result = execute_trial(graph.model_dump(), 0, 42, capture_ports=True)
    assert result["port_previews"]["custom"]["outputs"]["out"]["size"] == 8
    assert result["port_previews"]["custom"]["outputs"]["residual"]["size"] == 8


def test_python_ports_reject_invalid_declarations():
    with pytest.raises(PythonPortDefinitionError, match="duplicate"):
        parse_python_ports('PORTS = {"inputs": ["in", "in"]}')
    with pytest.raises(PythonPortDefinitionError, match="literal dictionary"):
        parse_python_ports("PORTS = make_ports()")


def test_python_port_cache_returns_fresh_mutable_lists():
    code = 'PORTS = {"inputs": ["left"], "outputs": ["right"]}'
    first = parse_python_ports(code)
    first.inputs.append("mutated")
    assert parse_python_ports(code).inputs == ["left"]


def test_python_runtime_parameters_are_validated():
    assert validate_parameters("python", {"output_size": "same", "runtime_executor": "threads", "runtime_batch_size": 0})
    assert validate_parameters("python", {"output_size": "same", "runtime_executor": "auto", "runtime_batch_size": 4097})


def test_advanced_signal_processing_and_fsk_blocks_preserve_contracts():
    context = make_context(np, np.random.default_rng(9), 0, 9, "cpu")
    bits = np.asarray([0, 1, 1, 0, 1, 0], dtype=np.int8)
    symbols = PROCESSORS["fsk2_mod"]({"in": bits}, {}, context)["out"]
    assert np.array_equal(PROCESSORS["fsk2_demod"]({"in": symbols}, {}, context)["out"], bits)

    biased = np.linspace(-1, 1, 64) + 3.0
    blocked = PROCESSORS["dc_blocker"]({"in": biased}, {"alpha": 0.99}, context)["out"]
    filtered = PROCESSORS["fir_filter"]({"in": blocked}, {"taps": "0.25,0.5,0.25"}, context)["out"]
    normalized = PROCESSORS["normalize_power"]({"in": filtered}, {"target_power": 2.0}, context)["out"]
    assert blocked.shape == filtered.shape == normalized.shape == biased.shape
    assert np.mean(np.abs(normalized) ** 2) == pytest.approx(2.0)


def test_convolutional_viterbi_round_trip_and_size_contract():
    context = make_context(np, np.random.default_rng(10), 0, 10, "cpu")
    bits = np.random.default_rng(11).integers(0, 2, 257, dtype=np.int8)
    encoded = PROCESSORS["convolutional_encode"]({"in": bits}, {}, context)
    decoded = PROCESSORS["viterbi_decode"]({"in": encoded["out"]}, {}, context)["out"]
    assert np.array_equal(decoded, bits)
    assert encoded["out"].size == bits.size * 2
    assert np.array_equal(encoded["reference"], bits)
    with pytest.raises(ValueError, match="multiple of 2"):
        validate_inputs("viterbi_decode", {"in": encoded["out"][:-1]}, {})


def test_rician_channel_and_evm_sink_report_modulation_quality():
    graph = Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": 128, "seed": 4}},
        {"id": "mod", "type": "qpsk_mod", "label": "QPSK", "params": {}},
        {"id": "channel", "type": "rician", "label": "Rician", "params": {"k_factor_db": 12, "flat": False, "ebn0_db": 18, "snr_mode": "fixed", "seed": 5}},
        {"id": "evm", "type": "evm_meter", "label": "EVM", "params": {}},
    ], edges=[
        {"id": "e1", "source": "source", "target": "mod"},
        {"id": "e2", "source": "mod", "target": "channel"},
        {"id": "e3", "source": "mod", "target": "evm", "target_handle": "reference"},
        {"id": "e4", "source": "channel", "target": "evm", "target_handle": "estimate"},
    ])
    result = run_once(graph, SimulationConfig(mode="specific_steps", max_frames=1, min_frames=1, engine="python", device="cpu"))
    assert result["sink_metrics"]["evm_symbol_count"] == 64
    assert 0 < result["sink_metrics"]["evm_rms_percent"] < 100
    assert math.isfinite(result["sink_metrics"]["evm_rms_db"])
    benchmark = run_simulation(graph, SimulationConfig(mode="specific_steps", max_frames=2, min_frames=2, workers=1, engine="python", device="cpu"))
    assert benchmark["sink_metrics"]["evm_symbol_count"] == 128
    assert benchmark["sink_metrics"]["evm_rms_percent"] > 0


@pytest.mark.parametrize(("block_type", "params"), [
    ("dc_blocker", {"alpha": 1.0}),
    ("fir_filter", {"taps": "0.5,nan"}),
    ("normalize_power", {"target_power": 0}),
    ("rician", {"k_factor_db": float("inf"), "ebn0_db": 4, "snr_mode": "fixed", "seed": 1}),
])
def test_advanced_block_parameters_are_validated(block_type, params):
    assert validate_parameters(block_type, params)


def test_validation_highlights_duplicate_variables_blocks():
    graph = Graph(nodes=[
        {"id": "first", "type": "variables", "label": "Variables A", "params": {"definitions": "rate = 1"}},
        {"id": "second", "type": "variables", "label": "Variables B", "params": {"definitions": "rate = 2"}},
    ], edges=[])
    validation = validate_graph(graph)
    assert not validation.valid
    assert "first" in validation.node_errors
    assert "second" in validation.node_errors


def test_file_source_and_classic_source_codecs_round_trip():
    context = make_context(np, np.random.default_rng(2), 0, 2, "cpu")
    raw = base64.b64encode(b"SignalLab").decode()
    source = PROCESSORS["text_file_source"]({}, {"data_base64": raw, "repeat": 1}, context)["out"]
    assert len(source) == 72
    for encoder, decoder in (("huffman_encode", "huffman_decode"), ("shannon_fano_encode", "shannon_fano_decode"), ("rle_encode", "rle_decode"), ("zip_encode", "zip_decode")):
        encoded = PROCESSORS[encoder]({"in": source}, {"weights": "8,4,2,1"}, context)["out"]
        decoded = PROCESSORS[decoder]({"in": encoded}, {"weights": "8,4,2,1"}, context)["out"]
        assert np.array_equal(decoded, source), encoder


def test_text_and_file_symbol_sources_emit_visible_characters():
    context = make_context(np, np.random.default_rng(3), 0, 3, "cpu")
    manual = PROCESSORS["text_symbol_source"]({}, {"text": "A B", "repeat": 2}, context)["out"]
    assert manual.dtype.kind == "U"
    assert manual.tolist() == list("A BA B")
    raw = base64.b64encode("Chào".encode("utf-8")).decode()
    file_symbols = PROCESSORS["text_file_symbol_source"]({}, {"data_base64": raw, "repeat": 1}, context)["out"]
    assert file_symbols.tolist() == list("Chào")


def test_discrete_source_and_information_analyzer_use_probability_model():
    context = make_context(np, np.random.default_rng(4), 0, 4, "cpu")
    params = {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125", "length": 5000, "seed": 42}
    symbols = PROCESSORS["discrete_symbol_source"]({}, params, context)["out"]
    assert abs(np.mean(symbols == "A") - 0.5) < 0.03
    analyzed = PROCESSORS["source_analyzer"]({"in": np.asarray(list("ABCD"))}, params, context)
    assert analyzed["probability"].tolist() == [0.5, 0.25, 0.125, 0.125]
    assert analyzed["information"].tolist() == [1.0, 2.0, 3.0, 3.0]
    assert analyzed["__metrics__"]["source_entropy_sum"] == pytest.approx(1.75)


@pytest.mark.parametrize("encoder,decoder", [
    ("symbol_huffman_encode", "symbol_huffman_decode"),
    ("symbol_shannon_fano_encode", "symbol_shannon_fano_decode"),
])
def test_text_symbol_codecs_round_trip(encoder, decoder):
    context = make_context(np, np.random.default_rng(5), 0, 5, "cpu")
    params = {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}
    source = np.asarray(list("ABACABAD"))
    encoded = PROCESSORS[encoder]({"in": source}, params, context)
    decoded = PROCESSORS[decoder]({"in": encoded["out"]}, params, context)["out"]
    assert encoded["reference"].tolist() == source.tolist()
    assert decoded.tolist() == source.tolist()


def test_symbol_huffman_defaults_to_pure_payload_and_supports_optional_header():
    context = make_context(np, np.random.default_rng(5), 0, 5, "cpu")
    base_params = {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125"}
    source = np.asarray(list("AAABCD"))

    encoded = PROCESSORS["symbol_huffman_encode"]({"in": source}, base_params, context)["out"]
    assert encoded.tolist() == [0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1]
    decoded = PROCESSORS["symbol_huffman_decode"]({"in": encoded}, base_params, context)["out"]
    assert decoded.tolist() == source.tolist()

    framed_params = {**base_params, "include_header": True}
    framed = PROCESSORS["symbol_huffman_encode"]({"in": source}, framed_params, context)["out"]
    assert len(framed) == 43
    assert framed[:32].tolist() == [int(bit) for bit in f"{len(source):032b}"]
    assert framed[32:].tolist() == encoded.tolist()
    framed_decoded = PROCESSORS["symbol_huffman_decode"]({"in": framed}, framed_params, context)["out"]
    assert framed_decoded.tolist() == source.tolist()


def test_symbol_huffman_rejects_an_incomplete_final_codeword():
    context = make_context(np, np.random.default_rng(5), 0, 5, "cpu")
    params = {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125", "include_header": False}
    with pytest.raises(ValueError, match="incomplete codeword"):
        PROCESSORS["symbol_huffman_decode"]({"in": np.asarray([1], dtype=np.int8)}, params, context)


def test_symbol_huffman_pure_payload_passes_full_graph_contracts():
    params = {"alphabet": "A,B,C,D", "probabilities": "0.5,0.25,0.125,0.125", "include_header": False}
    graph = Graph(nodes=[
        {"id": "source", "type": "text_symbol_source", "label": "Text", "params": {"text": "AAABCD", "repeat": 1}},
        {"id": "encoder", "type": "symbol_huffman_encode", "label": "Huffman encode", "params": params},
        {"id": "decoder", "type": "symbol_huffman_decode", "label": "Huffman decode", "params": params},
        {"id": "ser", "type": "ser", "label": "SER", "params": {}},
    ], edges=[
        {"id": "source-encoder", "source": "source", "target": "encoder", "source_handle": "out", "target_handle": "in"},
        {"id": "encoder-decoder", "source": "encoder", "target": "decoder", "source_handle": "out", "target_handle": "in"},
        {"id": "reference", "source": "encoder", "target": "ser", "source_handle": "reference", "target_handle": "reference"},
        {"id": "estimate", "source": "decoder", "target": "ser", "source_handle": "out", "target_handle": "estimate"},
    ])
    result = run_once(graph, SimulationConfig(seed=42, device="cpu"))
    assert result["port_previews"]["encoder"]["outputs"]["out"]["size"] == 11
    assert result["port_previews"]["encoder"]["inputs"]["in"]["sample"] == list("AAABCD")
    assert result["metrics"]["symbol_errors"] == 0


def test_symbols_to_bits_and_symbol_error_rate():
    context = make_context(np, np.random.default_rng(6), 0, 6, "cpu")
    symbols = np.asarray(list("Aé"))
    converted = PROCESSORS["symbols_to_bits"]({"in": symbols}, {"separator": ""}, context)
    expected = np.unpackbits(np.frombuffer("Aé".encode("utf-8"), dtype=np.uint8)).astype(np.int8)
    assert np.array_equal(converted["out"], expected)
    assert np.array_equal(converted["reference"], expected)
    metrics = PROCESSORS["ser"]({"reference": symbols, "estimate": np.asarray(list("Aê"))}, {}, context)["__metrics__"]
    assert metrics == {"symbol_errors": 1, "total_symbols": 2}


def test_symbol_model_contract_rejects_mismatched_probabilities():
    errors = validate_parameters("discrete_symbol_source", {"alphabet": "A,B,C", "probabilities": "0.5,0.5", "length": 10, "seed": -1})
    assert errors and "one value for every alphabet symbol" in errors[0]


def test_symbol_huffman_codebook_is_deterministic_for_equal_weights():
    assert _stable_huffman_codes([0.5, 0.25, 0.125, 0.125]) == {0: "0", 1: "10", 2: "110", 3: "111"}
    assert _stable_huffman_codes([0.4, 0.3, 0.2, 0.1]) == {0: "0", 1: "10", 3: "110", 2: "111"}


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_hamming_bpsk_is_deterministic_across_worker_counts():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 4096
    graph.nodes[3].params["snr_mode"] = "experiment"
    common = dict(
        mode="specific_steps",
        max_frames=64,
        min_frames=64,
        snr_db_start=2,
        chunk_size=8,
        device="cpu",
        engine="native",
        seed=2026,
    )
    serial = run_simulation(graph, SimulationConfig(**common, workers=1))
    parallel = run_simulation(graph, SimulationConfig(**common, workers=4))
    assert serial["engine"] == parallel["engine"] == "native_cpp"
    assert serial["bit_errors"] == parallel["bit_errors"]
    assert serial["total_bits"] == parallel["total_bits"] == 64 * 4096
    assert serial["port_previews"]["0"]["outputs"]["out"]["size"] == 4096


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_bpsk_ber_improves_with_snr():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 4096
    graph.nodes[3].params["snr_mode"] = "experiment"
    config = SimulationConfig(
        mode="ber_benchmark",
        max_frames=100,
        min_frames=100,
        min_errors=1_000_000,
        snr_db_start=0,
        snr_db_stop=6,
        snr_db_step=6,
        workers=4,
        chunk_size=10,
        device="cpu",
        engine="native",
        seed=2026,
    )
    result = run_simulation(graph, config)
    assert result["snr_points"][0]["ber"] > result["snr_points"][1]["ber"]


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_early_stop_honors_minimum_frames():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 4096
    graph.nodes[3].params["snr_mode"] = "experiment"
    result = run_simulation(graph, SimulationConfig(
        mode="ber_benchmark",
        max_frames=100,
        min_frames=10,
        min_errors=0,
        snr_db_start=2,
        snr_db_stop=2,
        workers=4,
        chunk_size=10,
        device="cpu",
        engine="native",
    ))
    assert result["snr_points"][0]["frames"] == 10


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_repetition3_pipeline_runs_fused():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 401
    graph.nodes[1].type = "repetition3_encode"
    graph.nodes[1].label = "Repetition-3 Encoder"
    graph.nodes[5].type = "repetition3_decode"
    graph.nodes[5].label = "Repetition-3 Decoder"
    graph.nodes[3].params["snr_mode"] = "experiment"
    result = run_simulation(graph, SimulationConfig(
        mode="specific_steps",
        max_frames=17,
        min_frames=17,
        snr_db_start=2,
        workers=4,
        chunk_size=5,
        device="cpu",
        engine="native",
        seed=2026,
    ))
    assert result["engine"] == "native_cpp"
    assert result["total_bits"] == 17 * 401


def _native_scientific_run(modulation: str, snr_db: float, workers: int = 4):
    return run_simulation(uncoded_modulation_graph(modulation, 4096), SimulationConfig(
        mode="specific_steps",
        max_frames=500,
        min_frames=500,
        snr_db_start=snr_db,
        workers=workers,
        chunk_size=50,
        device="cpu",
        engine="native",
        seed=2026,
    ))


def _assert_ber_within_confidence(result, expected: float):
    count = result["total_bits"]
    six_sigma = 6.0 * math.sqrt(expected * (1.0 - expected) / count)
    assert result["ber"] == pytest.approx(expected, abs=six_sigma + 2.0 / count)


def _qam16_theoretical_ber(snr_db: float) -> float:
    linear = 10.0 ** (snr_db / 10.0)
    sigma = math.sqrt(5.0 / linear)
    levels = (-3.0, -1.0, 3.0, 1.0)
    decoded = (0, 1, 3, 2)
    boundaries = (-math.inf, -2.0, 0.0, 2.0, math.inf)
    expected_errors_per_dimension = 0.0
    for source_state, level in enumerate(levels):
        for region, decoded_state in enumerate(decoded):
            low = 0.0 if math.isinf(boundaries[region]) else 0.5 * math.erfc(-(boundaries[region] - level) / (sigma * math.sqrt(2.0)))
            high = 1.0 if math.isinf(boundaries[region + 1]) else 0.5 * math.erfc(-(boundaries[region + 1] - level) / (sigma * math.sqrt(2.0)))
            expected_errors_per_dimension += 0.25 * (high - low) * ((source_state ^ decoded_state).bit_count())
    return expected_errors_per_dimension / 2.0


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
@pytest.mark.parametrize(("modulation", "snr_db", "theory"), [
    ("bpsk", 2.0, lambda value: 0.5 * math.erfc(math.sqrt(10.0 ** (value / 10.0)))),
    ("qpsk", 4.0, lambda value: 0.5 * math.erfc(math.sqrt(10.0 ** (value / 10.0) / 2.0))),
    ("qam16", 8.0, _qam16_theoretical_ber),
])
def test_native_awgn_ber_matches_theory(modulation, snr_db, theory):
    result = _native_scientific_run(modulation, snr_db)
    assert result["execution"]["modulation"] == modulation
    _assert_ber_within_confidence(result, theory(snr_db))


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_qam16_is_deterministic_across_worker_counts():
    serial = _native_scientific_run("qam16", 8.0, workers=1)
    parallel = _native_scientific_run("qam16", 8.0, workers=4)
    assert serial["bit_errors"] == parallel["bit_errors"]
    assert serial["total_bits"] == parallel["total_bits"]


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_hamming_qpsk_pipeline_runs_fused():
    graph = sample_graph()
    graph.nodes[0].params["length"] = 4096
    graph.nodes[2].type = "qpsk_mod"
    graph.nodes[2].label = "QPSK Modulator"
    graph.nodes[4].type = "qpsk_demod"
    graph.nodes[4].label = "QPSK Demodulator"
    graph.nodes[3].params["snr_mode"] = "experiment"
    result = run_simulation(graph, SimulationConfig(
        mode="specific_steps",
        max_frames=31,
        min_frames=31,
        snr_db_start=4,
        workers=4,
        chunk_size=8,
        device="cpu",
        engine="native",
        seed=2026,
    ))
    assert result["execution"] == {
        "backend": "cpp_onetbb",
        "version": "0.2.0",
        "modulation": "qpsk",
        "coding": "hamming74",
        "kernel": "fused_metric_only",
    }
    assert result["total_bits"] == 31 * 4096


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="native extension is not built")
def test_native_planner_rejects_extra_topology_edges():
    graph = uncoded_modulation_graph("qpsk")
    graph.edges.append(Edge(
        id="extra-channel-input",
        source="source",
        target="channel",
        source_handle="out",
        target_handle="in",
    ))
    plan, reason = compile_native_plan(graph, SimulationConfig(engine="native", device="cpu"))
    assert plan is None
    assert "without extra edges" in str(reason)


def test_forced_native_rejects_unsupported_graph():
    graph = Graph(
        nodes=[
            {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": 8}},
            {"id": "sink", "type": "power_meter", "label": "Power", "params": {}},
        ],
        edges=[{"id": "edge", "source": "source", "target": "sink", "source_handle": "out", "target_handle": "in"}],
    )
    with pytest.raises(ValueError, match="Native execution is unavailable"):
        run_simulation(graph, SimulationConfig(engine="native", device="cpu"))


def test_auto_reports_why_graph_fell_back_to_python():
    graph = Graph(
        nodes=[
            {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": 8}},
            {"id": "sink", "type": "power_meter", "label": "Power", "params": {}},
        ],
        edges=[{"id": "edge", "source": "source", "target": "sink", "source_handle": "out", "target_handle": "in"}],
    )
    result = run_simulation(graph, SimulationConfig(
        mode="specific_steps",
        max_frames=1,
        min_frames=1,
        engine="auto",
        device="cpu",
    ))
    assert result["engine"] == "python_numpy"
    assert "supports exact AWGN/BER chains" in result["execution"]["fallback_reason"]


def test_health_reports_native_capability():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    status = response.json()["native"]
    assert status["version"] == "0.2.0"
    assert "fused-qam16-awgn" in status["features"]
