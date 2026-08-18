# SignalLab

SignalLab is a local, visual digital-communications simulator inspired by Simulink and GNU Radio. Build a block graph in the browser, edit simple Python blocks, and run reproducible Monte-Carlo experiments on CPU or a compatible GPU.

Python Blocks include a CodeMirror-based IDE editor with Python syntax highlighting, line numbers, bracket matching and a large draft-based editing window.
At runtime they receive the current Experiment point through `params["snr_db"]` and related keys. A port-free Variables block declares safe typed globals shared by every Python Block without coupling user code to the parallel scheduler.

The interface uses a high-contrast light layout with a bundled SignalLab logo and app icon. Select a block and press `Delete` to remove it and its links.

Use **Open Samples** on the top bar to browse nine complete learning labs for BPSK/QPSK, channel coding, source entropy, Huffman/Shannon–Fano and custom Python blocks. Every sample includes learning objectives, guided steps and expected observations before it is opened as an editable simulation.

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
