import base64

from backend.app.blocks import PROCESSORS, make_context, python_block
from backend.app.engine import execute_trial, run_simulation, validate_graph
from backend.app.models import Edge, Graph, SimulationConfig
import numpy as np


def sample_graph():
    node_types = ["bit_source", "hamming74_encode", "bpsk_mod", "awgn", "bpsk_demod", "hamming74_decode", "ber"]
    nodes = [{"id": str(i), "type": kind, "label": kind, "params": {"length": 400, "ebn0_db": 20}} for i, kind in enumerate(node_types)]
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
