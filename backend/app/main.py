"""FastAPI entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import debug, generate, jobs, outline, roadmap, templates, upload
from app.config import get_settings
from app.logging_setup import setup_logging
from app.ollama_health import probe_ollama

setup_logging(get_settings().log_level)
log = logging.getLogger("ai-ppt-maker")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ai-ppt-maker", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/healthz")
    def healthz() -> dict:
        # ``model`` is the *configured* tag (echo of OLLAMA_MODEL). To tell
        # whether the daemon actually has a usable model, probe /api/tags.
        # The probe is best-effort (<2s, trust_env=False to dodge proxies)
        # and never raises — ``ollama.reachable=false`` is a valid answer.
        health = probe_ollama(settings.ollama_base_url, settings.ollama_model)
        return {
            "ok": True,
            "version": __version__,
            "model": settings.ollama_model,
            "ollama": health.to_dict(),
        }

    app.include_router(templates.router, prefix="/api", tags=["templates"])
    app.include_router(outline.router, prefix="/api", tags=["outline"])
    app.include_router(generate.router, prefix="/api", tags=["generate"])
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])
    app.include_router(debug.router, prefix="/api", tags=["debug"])
    app.include_router(roadmap.router, prefix="/api", tags=["roadmap"])

    # Serve frontend/dist if it exists (built via `npm run build` or scripts/deploy.*).
    # Lets a single uvicorn process serve both API and SPA — used by start.bat / start.sh.
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        bundle_dir = Path(__file__).resolve().parent.parent.parent
    dist_dir = bundle_dir / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

        @app.get("/")
        def _index() -> FileResponse:
            return FileResponse(dist_dir / "index.html")

        @app.get("/{full_path:path}")
        def _spa_fallback(full_path: str) -> FileResponse:
            target = dist_dir / full_path
            if target.is_file():
                return FileResponse(target)
            return FileResponse(dist_dir / "index.html")

        log.info("Serving SPA from %s", dist_dir)
    else:
        log.info("No frontend/dist found — backend serves API only (run `npm run build`)")

    log.info(
        "ai-ppt-maker backend %s ready (templates_dir=%s)", __version__, settings.templates_dir
    )
    return app


app = create_app()
