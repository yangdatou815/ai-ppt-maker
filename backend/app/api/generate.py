"""POST /api/generate — render an :class:`OutlineDoc` to .pptx and stream it back.

Synchronous in v0.3.0: render is fast (no LLM call, just python-pptx tree
serialisation) so we don't need the jobs queue yet. M3 will move to async +
``GET /api/jobs/{id}`` for thumbnail rendering via LibreOffice.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.templates import _scan_templates
from app.config import get_settings
from app.render.pptx_renderer import render_outline
from app.schemas.outline import OutlineDoc

log = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    outline: OutlineDoc
    template: str


def _safe_filename(title: str) -> str:
    """Turn an arbitrary outline title into a filesystem-safe basename.

    Keeps CJK characters — they're valid in filenames but the *Content-Disposition*
    header itself must be ASCII, see :func:`_content_disposition`.
    """
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", title).strip()
    cleaned = re.sub(r"\s+", "-", cleaned) or "ai-ppt-maker"
    # Browsers / Windows path limits — be conservative
    return cleaned[:60]


def _content_disposition(filename: str) -> str:
    """Build a header value that survives non-ASCII (RFC 5987 + ASCII fallback).

    Starlette refuses to encode non-latin-1 characters in headers, so we must
    pre-encode here. Browsers prefer ``filename*=UTF-8''…`` but old clients
    fall back to plain ``filename=…``.
    """
    ascii_fallback = re.sub(r"[^\x20-\x7e]", "_", filename) or "ai-ppt-maker.pptx"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.post("/generate")
def generate_pptx(req: GenerateRequest) -> Response:
    template = next((t for t in _scan_templates() if t.name == req.template), None)
    if template is None:
        raise HTTPException(status_code=404, detail=f"template '{req.template}' not found")

    t0 = time.perf_counter()
    try:
        uploads_dir = get_settings().workspace_dir / "uploads"
        data = render_outline(req.outline, template, uploads_dir=uploads_dir)
    except Exception as exc:  # noqa: BLE001 — surface as 500 with detail
        log.exception("render failed")
        raise HTTPException(status_code=500, detail=f"render failed: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    fname = _safe_filename(req.outline.title) + ".pptx"
    log.info(
        "generate done: template=%s sections=%d size_kb=%d elapsed_ms=%d",
        template.name, len(req.outline.sections), len(data) // 1024, elapsed_ms,
    )
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={
            "Content-Disposition": _content_disposition(fname),
            "X-Render-Elapsed-Ms": str(elapsed_ms),
            "X-Render-Template": template.name,
        },
    )
