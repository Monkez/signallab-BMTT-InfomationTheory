from backend.app.engine import execute_trial, run_simulation, validate_graph
from backend.app.models import Edge, Graph, SimulationConfig


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
    first = run_simulation(graph, config)
    second = run_simulation(graph, config)
    assert first["bit_errors"] == second["bit_errors"]
    assert first["total_bits"] == second["total_bits"]
    assert [point["snr_db"] for point in first["snr_points"]] == [0.0, 2.0, 4.0]


def test_cycle_is_rejected():
    graph = sample_graph()
    graph.edges.append(Edge(id="cycle", source="5", target="2"))
    assert not validate_graph(graph).valid
