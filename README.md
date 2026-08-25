# SignalLab

SignalLab is a local, visual digital-communications simulator inspired by Simulink and GNU Radio. Build a block graph in the browser, edit simple Python blocks, and run reproducible Monte-Carlo experiments on CPU or a compatible GPU.

For supported BPSK, QPSK, and 16-QAM BER pipelines, the Auto executor uses a fused C++20/oneTBB engine with counter-based Philox random streams, while arbitrary graphs continue to run through the Python/NumPy compatibility engine with an explicit fallback reason. See [Native CPU Engine](docs/NATIVE_ENGINE.md), run `benchmark.bat` for a local comparison, or use `benchmark_regression.bat` for the three-case performance gate.

Custom Python Blocks support persistent process workers and an optional vectorized `process_batch(signals, params_batch)` API. Run `benchmark_python.bat` to compare frame-inline, frame-auto, and batch-auto execution on the local CPU.

Python Blocks include a CodeMirror-based IDE editor with Python syntax highlighting, line numbers, bracket matching and a large draft-based editing window.
At runtime they receive the current Experiment point through `params["snr_db"]` and related keys. A port-free Variables block declares safe typed globals shared by every Python Block without coupling user code to the parallel scheduler.

The interface uses a high-contrast light layout with a bundled SignalLab logo and app icon. Numeric fields can be cleared naturally and accept scientific notation such as `1e6` or `1.52e3`. Monte-Carlo frame budgets no longer have a one-million-frame cap; a frame remains a user-visible graph boundary while the runtime batches tiny frames internally. The 61-block library includes PSK/QAM/OOK/2-FSK, convolutional/Viterbi coding, AWGN/Rayleigh/Rician channels, FIR/DC/power processing, FFT/IFFT/windowing, spectrum/waterfall analysis, BER/SER/EVM and custom Python processing.

Use **Open Samples** on the top bar to browse 14 complete learning labs. The library is grouped into Digital communications, Analog communications, Information theory and Python labs; AM/FM modulation examples are editable Python-block pipelines with Oscilloscope, Spectrum and BER views, while QPSK is covered by both AWGN and Rician labs. Every sample includes learning objectives, guided steps and expected observations before it is opened as an editable simulation.

## Quick start (Windows desktop)

1. Run `setup.bat` once.
2. Run `build_app.bat` once to create the desktop release.
3. Run `run.bat`, or open `dist\SignalLab\SignalLab.exe`.

Keep the complete `dist\SignalLab` directory together when copying the app. The EXE uses bundled runtime files in its `_internal` directory.

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for usage and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## Development

```powershell
.\.venv\Scripts\python -m pytest backend\tests
cd frontend
npm run build
```

Use `run_dev.bat` only for frontend/backend development with Vite hot reload. The optional CUDA path requires a CuPy package matching the installed CUDA toolkit. SignalLab falls back to CPU automatically when CuPy is unavailable.
