# SignalLab

SignalLab is a local, visual digital-communications simulator inspired by Simulink and GNU Radio. Build a block graph in the browser, edit simple Python blocks, and run reproducible Monte-Carlo experiments on CPU or a compatible GPU.

## Quick start (Windows)

1. Run `setup.bat` once.
2. Run `run.bat`.
3. Open <http://localhost:5173> (the script normally opens it for you).

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for usage and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## Development

```powershell
.\.venv\Scripts\python -m pytest backend\tests
cd frontend
npm run build
```

The optional CUDA path requires a CuPy package matching the installed CUDA toolkit. SignalLab falls back to CPU automatically when CuPy is unavailable.

