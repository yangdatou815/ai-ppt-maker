"""Launcher entry point for PyInstaller bundle.

When frozen (running from PyInstaller bundle), adjusts paths so that:
- templates_dir points to bundled backend/templates/
- frontend/dist is found relative to the bundle dir

Then starts uvicorn on port 8080.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _setup_bundle_paths():
    """Configure environment for PyInstaller frozen mode."""
    if getattr(sys, "frozen", False):
        # Running from bundle — _MEIPASS is the temp extraction dir (onefile)
        # or the bundle dir (onedir)
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        # Dev mode — running from source
        bundle_dir = Path(__file__).resolve().parent.parent

    # Set environment overrides so app.config picks up bundled paths
    templates_dir = bundle_dir / "backend" / "templates"
    if templates_dir.is_dir():
        os.environ.setdefault("TEMPLATES_DIR", str(templates_dir))

    # Workspace for generated files
    workspace = Path.home() / ".ai-ppt-maker" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("WORKSPACE_DIR", str(workspace))

    # Ensure proxy bypass for local Ollama
    os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
    os.environ.setdefault("no_proxy", "127.0.0.1,localhost")


def main():
    _setup_bundle_paths()

    import uvicorn

    from app.main import app  # noqa: F401 — imported for uvicorn

    port = int(os.environ.get("APP_PORT", "8080"))
    host = os.environ.get("APP_HOST", "127.0.0.1")

    print(f"\n  ai-ppt-maker v{_get_version()} starting...")
    print(f"  Host: {host}:{port}")
    print(f"  Frozen: {getattr(sys, 'frozen', False)}")
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
        print(f"  Bundle dir: {bundle_dir}")
        dist_dir = bundle_dir / "frontend" / "dist"
        print(f"  Frontend dist: {dist_dir} (exists={dist_dir.is_dir()})")
    print(f"\n  Open in browser: http://127.0.0.1:{port}")
    print("  Press Ctrl+C to stop\n")

    # Auto-open browser after a short delay
    import threading
    import webbrowser

    def _open_browser():
        import time

        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


def _get_version() -> str:
    try:
        from app import __version__

        return __version__
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
