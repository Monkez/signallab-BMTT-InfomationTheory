import base64

import pytest
from fastapi.testclient import TestClient

from backend.app.blocks import PROCESSORS, _stable_huffman_codes, make_context, python_block
from backend.app.block_registry import SPEC_BY_TYPE
from backend.app.contracts import BlockExecutionError
from backend.app.contracts import validate_inputs, validate_outputs, validate_parameters
from backend.app.engine import execute_trial, run_once, run_simulation, validate_graph
from backend.app.models import Edge, Graph, SimulationConfig
from backend.app.main import app
import numpy as np


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
    )
    updates = []
    first = run_simulation(graph, config, progress=updates.append)
    second = run_simulation(graph, config)
    assert first["bit_errors"] == second["bit_errors"]
    assert first["total_bits"] == second["total_bits"]
    assert [point["snr_db"] for point in first["snr_points"]] == [0.0, 2.0, 4.0]
    assert updates and updates[-1]["snr_points"][-1]["frames"] >= 1
    assert first["port_previews"]["0"]["outputs"]["out"]["shape"] == [400]


def test_run_once_captures_input_and_output_port_samples():
    result = run_once(sample_graph(), SimulationConfig(seed=42, device="cpu"))
    source = result["port_previews"]["0"]["outputs"]["out"]
    decoder_input = result["port_previews"]["5"]["inputs"]["in"]
    assert source["dtype"] == "int8"
    assert source["shape"] == [400]
    assert len(source["sample"]) == 8
    assert decoder_input["size"] == 700
    assert result["_port_values"]["1"]["inputs"]["in"] is result["_port_values"]["0"]["outputs"]["out"]


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
    ("awgn", np.ones(8, dtype=np.float32), 8),
    ("rayleigh", np.ones(8, dtype=np.float32), 8),
    ("bpsk_demod", np.ones(8, dtype=np.float32), 8),
    ("qpsk_demod", np.ones(4, dtype=np.complex64), 8),
])
def test_builtin_signal_processors_obey_declared_size_contract(block_type, signal, expected_size):
    context = make_context(np, np.random.default_rng(7), 0, 7, "cpu", 4.0)
    inputs = {"in": signal}
    validate_inputs(block_type, inputs, {})
    outputs = PROCESSORS[block_type](inputs, {}, context)
    validate_outputs(block_type, inputs, outputs, SPEC_BY_TYPE[block_type].outputs, {})
    assert outputs["out"].size == expected_size


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
