"""POST /api/upload — store an image for later embed in a slide.

The renderer reads files by ``file_id`` from ``<workspace_dir>/uploads/``.
We accept only the image MIME types python-pptx can embed without conversion.
Size is capped by :data:`Settings.max_upload_mb` (defaults to 50 MB).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter()


# python-pptx embeds these without any external conversion. SVG / TIFF are
# excluded on purpose — they need rasterisation we don't run server-side.
_ALLOWED_MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _uploads_dir() -> Path:
    d = get_settings().workspace_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/upload")
async def upload_image(file: UploadFile) -> dict:
    settings = get_settings()
    ctype = (file.content_type or "").lower()
    if ctype not in _ALLOWED_MIME_EXT:
        raise HTTPException(
            status_code=415,
            detail=(
                f"unsupported content-type '{ctype}'. "
                f"Allowed: {sorted(_ALLOWED_MIME_EXT)}"
            ),
        )

    # Stream-read with a hard cap so a malicious / fat upload can't OOM us.
    cap = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds {settings.max_upload_mb} MB cap",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="empty file")

    ext = _ALLOWED_MIME_EXT[ctype]
    file_id = uuid.uuid4().hex
    target = _uploads_dir() / f"{file_id}{ext}"
    target.write_bytes(b"".join(chunks))
    log.info("upload stored: file_id=%s bytes=%d ctype=%s", file_id, total, ctype)
    return {"file_id": f"{file_id}{ext}", "bytes": total, "content_type": ctype}
