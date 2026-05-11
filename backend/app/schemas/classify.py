"""Schemas for /api/classify-template — pick the best template for source text."""
from __future__ import annotations

from pydantic import BaseModel, Field

# Kept in sync with the template registry in backend/templates/.
ALLOWED_TEMPLATES = ("executive-dark", "minimal-light", "tech-blue")


class ClassifyTemplateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    language: str = "auto"


class ClassifyTemplateResponse(BaseModel):
    template: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    used_fallback: bool
    used_model: str | None = None
    elapsed_ms: int
