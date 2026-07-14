# desktop/app.py — native desktop shell (pywebview + local Flask)
"""Launch GameGent as a desktop window on http://127.0.0.1:5000."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _frontend_is_stale(root: str) -> bool:
    """True if React dist is missing or older than source/package files."""
    index = os.path.join(root, "web", "react-app", "dist", "index.html")
    if not os.path.isfile(index):
        return True

    dist_mtime = os.path.getmtime(index)
    react_root = os.path.join(root, "web", "react-app")
    watch = [
        os.path.join(react_root, "package.json"),
        os.path.join(react_root, "package-lock.json"),
        os.path.join(react_root, "vite.config.ts"),
        os.path.join(react_root, "index.html"),
    ]
    for path in watch:
        if os.path.isfile(path) and os.path.getmtime(path) > dist_mtime:
            return True

    src_dir = os.path.join(react_root, "src")
    for dirpath, _, filenames in os.walk(src_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.getmtime(path) > dist_mtime:
                return True
    return False


def _ensure_frontend_build(root: str) -> None:
    index = os.path.join(root, "web", "react-app", "dist", "index.html")
    if not _frontend_is_stale(root):
        return

    npm = shutil.which("npm")
    if not npm:
        if os.path.isfile(index):
            print("Warning: frontend looks stale but npm not found; using existing dist/")
            return
        raise SystemExit("React build missing and npm not found. Run: cd web/react-app && npm run build")

    print("Building frontend…")
    build = subprocess.run([npm, "run", "build"], cwd=os.path.join(root, "web", "react-app"))
    if build.returncode != 0:
        raise SystemExit(build.returncode)
    if not os.path.isfile(index):
        raise SystemExit("Frontend build failed: dist/index.html not found")


def _wait_for_server(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/api/status", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.1)
    raise SystemExit(f"Timed out waiting for GameGent server at {URL}")


def _run_flask(root: str) -> threading.Thread:
    # Import after dist exists so Flask picks USE_REACT=True
    if root not in sys.path:
        sys.path.insert(0, root)

    from werkzeug.serving import make_server
    from web.app import app

    server = make_server(HOST, PORT, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Attach for shutdown
    thread.server = server  # type: ignore[attr-defined]
    return thread


def _import_webview():
    try:
        import webview
        return webview
    except ImportError as exc:
        root = _project_root()
        raise SystemExit(
            "pywebview is required for the desktop app, and must be installed in the project venv.\n"
            f"  {root}/venv/bin/pip install -r requirements.txt\n"
            "Do not use system pip (Arch blocks it). Then re-run: gamegent app"
        ) from exc


def _pick_gui() -> str | None:
    """Prefer a GUI backend that actually imports in this environment."""
    forced = os.environ.get("PYWEBVIEW_GUI")
    if forced:
        return forced

    # GTK (gi) or Qt from system packages — needs include-system-site-packages=true
    try:
        import gi  # noqa: F401
        return "gtk"
    except ImportError:
        pass

    for mod in ("PyQt6", "PyQt5", "PySide6", "PySide2"):
        try:
            __import__(mod)
            return "qt"
        except ImportError:
            continue

    return None


def run_desktop_app() -> None:
    """Start Flask on localhost and open a pywebview window."""
    webview = _import_webview()
    root = _project_root()
    _ensure_frontend_build(root)

    gui = _pick_gui()
    if gui is None:
        raise SystemExit(
            "pywebview is installed, but no window backend is available.\n"
            "On Arch, install one of:\n"
            "  sudo pacman -S python-gobject webkit2gtk-4.1\n"
            "  sudo pacman -S python-pyqt6\n"
            "And enable system site packages in the venv (already set if you use this repo's venv):\n"
            "  include-system-site-packages = true   in venv/pyvenv.cfg"
        )

    flask_thread = _run_flask(root)
    _wait_for_server()

    webview.create_window(
        "GameGent",
        URL,
        width=1180,
        height=820,
        min_size=(800, 600),
    )
    try:
        webview.start(gui=gui)
    except Exception as exc:
        server = getattr(flask_thread, "server", None)
        if server is not None:
            server.shutdown()
        raise SystemExit(f"Failed to start desktop window ({gui}): {exc}") from exc

    server = getattr(flask_thread, "server", None)
    if server is not None:
        server.shutdown()


if __name__ == "__main__":
    run_desktop_app()
