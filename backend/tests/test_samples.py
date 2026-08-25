import json
from pathlib import Path

from backend.app.engine import run_once, run_simulation, validate_graph
from backend.app.models import Graph, SimulationConfig


CATALOG_PATH = Path(__file__).parents[2] / "samples" / "catalog.json"


def test_learning_sample_catalog_is_complete_and_executable():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ids = [project["sample"]["id"] for project in catalog]

    assert len(catalog) >= 9
    assert len(ids) == len(set(ids))
    assert {project["sample"]["category"] for project in catalog} == {
        "Digital communications", "Analog communications", "Information theory", "Python labs",
    }
    assert sum(bool(project["sample"]["uses_python"]) for project in catalog) >= 2

    for project in catalog:
        metadata = project["sample"]
        assert len(metadata["learning_objectives"]) >= 3
        assert len(metadata["instructions"]) >= 4
        assert len(metadata["expected_observations"]) >= 2

        graph = Graph.model_validate(project["graph"])
        config = SimulationConfig.model_validate(project["config"])
        assert config.mode in {"specific_steps", "ber_benchmark"}
        assert config.snr_db_points
        validation = validate_graph(graph)
        assert validation.valid, f"{metadata['id']}: {validation.errors}"
        result = run_once(graph, config)
        assert result["port_previews"]


def test_shannon_fano_learning_sample_uses_matching_framing():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    project = next(item for item in catalog if item["sample"]["id"] == "shannon-fano-symbol-roundtrip")
    codec_nodes = [node for node in project["graph"]["nodes"] if "shannon_fano" in node["type"]]

    assert len(codec_nodes) == 2
    assert all(node["params"]["include_header"] is True for node in codec_nodes)


def test_every_learning_sample_completes_a_short_benchmark():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for project in catalog:
        graph = Graph.model_validate(project["graph"])
        original = SimulationConfig.model_validate(project["config"])
        config = original.model_copy(update={
            "mode": "specific_steps",
            "trials": 2,
            "max_frames": 2,
            "min_frames": 2,
            "min_errors": 0,
            "snr_db_stop": original.snr_db_start,
            "workers": 1,
            "engine": "python",
            "chunk_size": 2,
        })
        result = run_simulation(graph, config)
        assert result["completed_trials"] == 2, project["sample"]["id"]
        assert not result["cancelled"], project["sample"]["id"]
