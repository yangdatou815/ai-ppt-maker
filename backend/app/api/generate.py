"""Generation endpoint — returns the rendered .pptx (M2-2, not yet implemented)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/generate")
def generate_pptx() -> dict:
    raise HTTPException(
        status_code=501,
        detail="POST /api/generate is not implemented yet (M2-2 milestone).",
    )
