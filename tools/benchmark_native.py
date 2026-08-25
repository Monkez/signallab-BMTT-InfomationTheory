from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass

from backend.app.engine import run_simulation
from backend.app.models import Graph, SimulationConfig
from backend.app.native_engine import native_status


@dataclass(frozen=True)
class Case:
    bits: int
    frames: int


def benchmark_graph(bits: int, modulation: str, coding: str) -> Graph:
    modulator, demodulator = {
        "bpsk": ("bpsk_mod", "bpsk_demod"),
        "qpsk": ("qpsk_mod", "qpsk_demod"),
        "qam16": ("qam16_mod", "qam16_demod"),
    }[modulation]
    coding_pair = {
        "none": (),
        "hamming74": ("hamming74_encode", "hamming74_decode"),
        "repetition3": ("repetition3_encode", "repetition3_decode"),
    }[coding]
    kinds = ["bit_source", *coding_pair[:1], modulator, "awgn", demodulator, *coding_pair[1:], "ber"]
    nodes = [
        {"id": str(index), "type": kind, "label": kind, "params": {"length": bits, "ebn0_db": 2, "snr_mode": "experiment", "seed": 123}}
        for index, kind in enumerate(kinds)
    ]
    source, meter = "0", str(len(kinds) - 1)
    encoder = "1" if coding_pair else None
    mod = "2" if encoder else "1"
    channel = str(int(mod) + 1)
    demod = str(int(channel) + 1)
    decoder = str(int(demod) + 1) if encoder else None
    edges = [
        {"id": "source-path", "source": source, "target": encoder or mod, "source_handle": "out", "target_handle": "in"},
        *([{"id": "encoder-mod", "source": encoder, "target": mod, "source_handle": "out", "target_handle": "in"}] if encoder else []),
        {"id": "mod-channel", "source": mod, "target": channel, "source_handle": "out", "target_handle": "in"},
        {"id": "channel-demod", "source": channel, "target": demod, "source_handle": "out", "target_handle": "in"},
        *([{"id": "demod-decoder", "source": demod, "target": decoder, "source_handle": "out", "target_handle": "in"}] if decoder else []),
        {"id": "reference", "source": encoder or source, "target": meter, "source_handle": "reference" if encoder else "out", "target_handle": "reference"},
        {"id": "estimate", "source": decoder or demod, "target": meter, "source_handle": "out", "target_handle": "estimate"},
    ]
    return Graph(nodes=nodes, edges=edges)


def measure(case: Case, engine: str, workers: int, modulation: str, coding: str) -> dict[str, object]:
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
    result = run_simulation(benchmark_graph(case.bits, modulation, coding), config)
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


def measure_repeated(case: Case, engine: str, workers: int, modulation: str, coding: str, repeats: int) -> dict[str, object]:
    # Warm imports, allocator state, and the oneTBB arena before collecting a
    # robust median. The warm-up is intentionally not reported.
    measure(Case(case.bits, min(8, case.frames)), engine, workers, modulation, coding)
    runs = [measure(case, engine, workers, modulation, coding) for _ in range(repeats)]
    representative = dict(runs[0])
    representative["elapsed_seconds"] = round(statistics.median(float(row["elapsed_seconds"]) for row in runs), 6)
    representative["throughput_mbps"] = round(statistics.median(float(row["throughput_mbps"]) for row in runs), 3)
    representative["repeats"] = repeats
    representative["throughput_min_mbps"] = min(float(row["throughput_mbps"]) for row in runs)
    representative["throughput_max_mbps"] = max(float(row["throughput_mbps"]) for row in runs)
    return representative


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare SignalLab Python and fused native Monte-Carlo engines.")
    parser.add_argument("--bits", type=int, default=4096)
    parser.add_argument("--frames", type=int, default=1000)
    parser.add_argument("--modulation", choices=("bpsk", "qpsk", "qam16"), default="bpsk")
    parser.add_argument("--coding", choices=("none", "hamming74", "repetition3"), default="hamming74")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--min-speedup", type=float, default=0.0, help="Exit with code 2 when native median speedup is lower")
    parser.add_argument("--json", action="store_true", help="Print JSON lines only")
    args = parser.parse_args()
    case = Case(bits=args.bits, frames=args.frames)
    if args.bits <= 0 or args.frames <= 0 or args.repeats <= 0:
        parser.error("bits, frames, and repeats must be positive")
    if args.modulation == "qam16" and args.coding != "none":
        parser.error("native 16-QAM currently supports --coding none")
    status = native_status()
    if not status.get("available"):
        raise SystemExit(f"Native engine unavailable: {status.get('reason')}")
    rows = [
        measure_repeated(case, "python", 1, args.modulation, args.coding, args.repeats),
        measure_repeated(case, "native", 0, args.modulation, args.coding, args.repeats),
    ]
    if args.json:
        for row in rows:
            print(json.dumps(row))
    else:
        print(f"SignalLab native benchmark - {args.coding} {args.modulation.upper()} - {case.frames} frames x {case.bits} bits - median of {args.repeats}")
        for row in rows:
            print(f"  {row['actual']:<24} {row['throughput_mbps']:>10.3f} Mbit/s - {row['elapsed_seconds']:.6f} s - {row['workers']} worker(s)")
    speedup = float(rows[1]["throughput_mbps"]) / max(float(rows[0]["throughput_mbps"]), 1e-12)
    if not args.json:
        print(f"  Native speedup: {speedup:.2f}x")
    if speedup < args.min_speedup:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
