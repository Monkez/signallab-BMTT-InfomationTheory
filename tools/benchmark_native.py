from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from backend.app.engine import run_simulation
from backend.app.models import Graph, SimulationConfig
from backend.app.native_engine import native_status


@dataclass(frozen=True)
class Case:
    bits: int
    frames: int


def benchmark_graph(bits: int) -> Graph:
    kinds = ["bit_source", "hamming74_encode", "bpsk_mod", "awgn", "bpsk_demod", "hamming74_decode", "ber"]
    nodes = [
        {"id": str(index), "type": kind, "label": kind, "params": {"length": bits, "ebn0_db": 2, "snr_mode": "experiment", "seed": 123}}
        for index, kind in enumerate(kinds)
    ]
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


def measure(case: Case, engine: str, workers: int) -> dict[str, object]:
    config = SimulationConfig(
        mode="specific_steps",
        max_frames=case.frames,
        min_frames=case.frames,
        snr_db_start=2,
        workers=workers,
        chunk_size=10,
        device="cpu",
        engine=engine,
        seed=2026,
    )
    result = run_simulation(benchmark_graph(case.bits), config)
    return {
        "requested": engine,
        "actual": result["engine"],
        "bits_per_frame": case.bits,
        "frames": case.frames,
        "workers": result["workers"],
        "elapsed_seconds": round(result["elapsed_seconds"], 6),
        "throughput_mbps": round(result["throughput_bps"] / 1_000_000, 3),
        "ber": result["ber"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare SignalLab Python and fused native Monte-Carlo engines.")
    parser.add_argument("--bits", type=int, default=4096)
    parser.add_argument("--frames", type=int, default=1000)
    parser.add_argument("--json", action="store_true", help="Print JSON lines only")
    args = parser.parse_args()
    case = Case(bits=args.bits, frames=args.frames)
    status = native_status()
    if not status.get("available"):
        raise SystemExit(f"Native engine unavailable: {status.get('reason')}")
    rows = [measure(case, "python", 1), measure(case, "native", 0)]
    if args.json:
        for row in rows:
            print(json.dumps(row))
        return
    print(f"SignalLab native benchmark - {case.frames} frames x {case.bits} bits")
    for row in rows:
        print(f"  {row['actual']:<24} {row['throughput_mbps']:>10.3f} Mbit/s - {row['elapsed_seconds']:.6f} s - {row['workers']} worker(s)")
    speedup = float(rows[1]["throughput_mbps"]) / max(float(rows[0]["throughput_mbps"]), 1e-12)
    print(f"  Native speedup: {speedup:.2f}x")


if __name__ == "__main__":
    main()
