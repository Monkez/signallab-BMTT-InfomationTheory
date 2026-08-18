"""SignalLab Windows desktop entry point.

The bundled app serves the production frontend and API from one private
loopback address, then opens it inside the native Edge WebView2 window.
"""

from __future__ import annotations

import multiprocessing
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview
from fastapi.staticfiles import StaticFiles

from backend.app.main import app
from backend.app.project_files import read_project_text, write_project_text


PROJECT_FILE_TYPES = (
    "SignalLab simulation (*.json)",
)


class DesktopProjectApi:
    def __init__(self) -> None:
        self._current_path: Path | None = None
        self._lock = threading.Lock()

    def open_project(self) -> dict[str, object]:
        selection = webview.windows[0].create_file_dialog(webview.FileDialog.OPEN, file_types=PROJECT_FILE_TYPES)
        if not selection:
            return {"cancelled": True}
        path = Path(selection[0]).resolve()
        content = read_project_text(path)
        with self._lock:
            self._current_path = path
        return {"cancelled": False, "content": content, "name": path.name, "path": str(path)}

    def save_project(self, content: str, save_as: bool = False, suggested_name: str = "untitled-simulation.slab.json") -> dict[str, object]:
        with self._lock:
            path = self._current_path
        if save_as or path is None:
            selection = webview.windows[0].create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=suggested_name,
                file_types=PROJECT_FILE_TYPES,
            )
            if not selection:
                return {"cancelled": True}
            path = Path(selection[0]).resolve()
        path = write_project_text(path, content)
        with self._lock:
            self._current_path = path
        return {"cancelled": False, "name": path.name, "path": str(path), "direct": True}

    def clear_project_path(self) -> None:
        with self._lock:
            self._current_path = None


def resource_path(*parts: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root.joinpath(*parts)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("SignalLab local service did not start in time")


def run() -> None:
    frontend = resource_path("frontend", "dist")
    if not (frontend / "index.html").exists():
        raise FileNotFoundError(f"Production frontend not found: {frontend}")

    # API routes were registered first, so the root mount only handles UI files.
    app.mount("/", StaticFiles(directory=frontend, html=True), name="desktop-ui")
    port = free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    server_thread = threading.Thread(target=server.run, name="signallab-api", daemon=True)
    server_thread.start()
    wait_until_ready(port)

    project_api = DesktopProjectApi()
    webview.create_window(
        "SignalLab — Digital Communications Studio",
        f"http://127.0.0.1:{port}",
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#f4f6f8",
        js_api=project_api,
    )
    try:
        webview.start(gui="edgechromium", debug=False, private_mode=False)
    finally:
        server.should_exit = True
        server_thread.join(timeout=3)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
