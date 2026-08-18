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

STARTUP_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:Segoe UI,Arial,sans-serif;background:#f6f8fb;color:#23344b}
body{display:flex;align-items:center;justify-content:center}.loading{text-align:center}.logo{width:56px;height:56px;margin:0 auto 14px;border-radius:14px;background:#23344b;display:grid;place-items:center;color:#fff;font-size:28px;font-weight:700}.logo:before{content:'∿';transform:translateY(-2px)}h1{font-size:24px;letter-spacing:-.03em;margin:0 0 5px}p{color:#718096;font-size:11px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 18px}.bar{width:44px;height:3px;margin:auto;border-radius:3px;background:#d8e2ef;overflow:hidden}.bar:after{content:'';display:block;width:50%;height:100%;background:#3572d1;border-radius:inherit;animation:load .45s ease-in-out infinite}@keyframes load{0%{transform:translateX(-100%)}100%{transform:translateX(200%)}}
</style></head><body><main class="loading"><div class="logo"></div><h1>SignalLab</h1><p>Digital Communications Studio</p><div class="bar"></div></main></body></html>"""


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


def load_frontend_when_ready(window: webview.Window, port: int) -> None:
    """Keep the native loading window visible while the local API boots."""
    try:
        wait_until_ready(port)
        window.load_url(f"http://127.0.0.1:{port}")
    except Exception as exc:  # pragma: no cover - only reachable during desktop startup
        message = str(exc).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        window.load_html(f"<html><body style='font:14px Segoe UI;padding:32px;color:#23344b'><h2>SignalLab could not start</h2><p>{message}</p></body></html>")


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

    project_api = DesktopProjectApi()
    window = webview.create_window(
        "SignalLab — Digital Communications Studio",
        html=STARTUP_HTML,
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#f4f6f8",
        js_api=project_api,
    )
    try:
        webview.start(
            func=lambda: threading.Thread(target=load_frontend_when_ready, args=(window, port), daemon=True).start(),
            gui="edgechromium",
            debug=False,
            private_mode=False,
        )
    finally:
        server.should_exit = True
        server_thread.join(timeout=3)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
