"""FastAPI entry point."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import generate, jobs, outline, templates
from app.config import get_settings
from app.logging_setup import setup_logging

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
        return {"ok": True, "version": __version__, "model": settings.ollama_model}

    app.include_router(templates.router, prefix="/api", tags=["templates"])
    app.include_router(outline.router, prefix="/api", tags=["outline"])
    app.include_router(generate.router, prefix="/api", tags=["generate"])
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])

    # Serve frontend/dist if it exists (built via `npm run build` or scripts/deploy.*).
    # Lets a single uvicorn process serve both API and SPA — used by start.bat / start.sh.
    repo_root = Path(__file__).resolve().parent.parent.parent
    dist_dir = repo_root / "frontend" / "dist"
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

    log.info("ai-ppt-maker backend %s ready (templates_dir=%s)", __version__, settings.templates_dir)
    return app


app = create_app()
