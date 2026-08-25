from __future__ import annotations

import argparse
import statistics

from backend.app.engine import run_simulation
from backend.app.models import Graph, SimulationConfig


THRESHOLD_CODE = """def process(signal, params):
    return (np.asarray(signal) < 0).astype(np.int8)
"""

FFT_CODE = """def process(signal, params):
    values = np.asarray(signal)
    restored = np.fft.ifft(np.fft.fft(values))
    return (np.real(restored) < 0).astype(np.int8)
"""


THRESHOLD_BATCH_CODE = THRESHOLD_CODE + """
def process_batch(signals, params_batch):
    return (np.asarray(signals) < 0).astype(np.int8)
"""

FFT_BATCH_CODE = FFT_CODE + """
def process_batch(signals, params_batch):
    values = np.asarray(signals)
    restored = np.fft.ifft(np.fft.fft(values, axis=1), axis=1)
    return (np.real(restored) < 0).astype(np.int8)
"""


def benchmark_graph(bits: int, workload: str, batch_api: bool = False) -> Graph:
    code = FFT_CODE if workload == "fft" else THRESHOLD_CODE
    if batch_api:
        code = FFT_BATCH_CODE if workload == "fft" else THRESHOLD_BATCH_CODE
    return Graph(nodes=[
        {"id": "source", "type": "bit_source", "label": "Bits", "params": {"length": bits, "seed": 123}},
        {"id": "mod", "type": "bpsk_mod", "label": "BPSK", "params": {}},
        {"id": "channel", "type": "awgn", "label": "AWGN", "params": {"ebn0_db": 2, "snr_mode": "experiment", "seed": 456}},
        {"id": "custom", "type": "python", "label": f"Python {workload}", "params": {"output_size": "same"}, "code": code},
        {"id": "meter", "type": "ber", "label": "BER", "params": {}},
    ], edges=[
        {"id": "e1", "source": "source", "target": "mod"},
        {"id": "e2", "source": "mod", "target": "channel"},
        {"id": "e3", "source": "channel", "target": "custom"},
        {"id": "e4", "source": "source", "target": "meter", "target_handle": "reference"},
        {"id": "e5", "source": "custom", "target": "meter", "target_handle": "estimate"},
    ])


def measure(bits: int, frames: int, workload: str, workers: int, batch_api: bool = False) -> dict[str, float | int | str]:
    result = run_simulation(benchmark_graph(bits, workload, batch_api), SimulationConfig(
        mode="specific_steps",
        max_frames=frames,
        min_frames=frames,
        snr_db_start=2,
        workers=workers,
        chunk_size=8,
        device="cpu",
        engine="python",
        seed=2026,
    ))
    return {
        "engine": result["engine"],
        "workers": result["workers"],
        "scheduler": result["execution"]["scheduler"],
        "api": "process_batch" if batch_api else "process",
        "elapsed": result["elapsed_seconds"],
        "throughput_mbps": result["throughput_bps"] / 1_000_000,
    }


def median_measure(bits: int, frames: int, workload: str, workers: int, repeats: int, batch_api: bool = False) -> dict[str, float | int | str]:
    measure(bits, min(8, frames), workload, 1, batch_api)
    rows = [measure(bits, frames, workload, workers, batch_api) for _ in range(repeats)]
    result = dict(rows[0])
    result["elapsed"] = statistics.median(float(row["elapsed"]) for row in rows)
    result["throughput_mbps"] = statistics.median(float(row["throughput_mbps"]) for row in rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SignalLab custom Python Block scheduling.")
    parser.add_argument("--bits", type=int, default=65_536)
    parser.add_argument("--frames", type=int, default=256)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workload", choices=("threshold", "fft"), default="fft")
    parser.add_argument("--min-speedup", type=float, default=0.0)
    args = parser.parse_args()
    if args.bits <= 0 or args.frames <= 0 or args.repeats <= 0:
        parser.error("bits, frames, and repeats must be positive")
    serial = median_measure(args.bits, args.frames, args.workload, 1, args.repeats)
    automatic = median_measure(args.bits, args.frames, args.workload, 0, args.repeats)
    batched = median_measure(args.bits, args.frames, args.workload, 0, args.repeats, batch_api=True)
    speedup = float(batched["throughput_mbps"]) / max(float(serial["throughput_mbps"]), 1e-12)
    print(f"SignalLab Python Block benchmark - {args.workload} - {args.frames} frames x {args.bits} samples - median of {args.repeats}")
    for name, row in (("frame serial", serial), ("frame auto", automatic), ("batch auto", batched)):
        print(f"  {name:<12} {row['throughput_mbps']:>10.3f} Msamples/s - {row['elapsed']:.6f} s - {row['workers']} worker(s) - {row['scheduler']}")
    print(f"  Batch-auto vs frame-serial speedup: {speedup:.2f}x")
    if speedup < args.min_speedup:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
