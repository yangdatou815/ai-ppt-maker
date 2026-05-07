"""Outline generation orchestrator: source -> LLM (with repair) -> fallback."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.outline.fallback import rule_based
from app.outline.llm_client import LlmUnavailableError, OllamaClient
from app.outline.prompts import SYSTEM_PROMPT, build_user_message
from app.outline.repair import JsonRepairError, repair
from app.schemas.outline import OutlineDoc

log = logging.getLogger(__name__)
router = APIRouter()

_MAX_CONTENT_CHARS = 20_000


class OutlineRequest(BaseModel):
    source_type: str = "text"
    content: str = Field(..., min_length=1)
    language: str = "auto"


class OutlineResponse(BaseModel):
    outline: OutlineDoc
    used_fallback: bool
    used_model: str | None = None
    elapsed_ms: int


def _default_client() -> OllamaClient:
    s = get_settings()
    return OllamaClient(s.ollama_base_url, s.ollama_model, s.ollama_timeout_s)


# Tests can inject a stub client without monkey-patching imports.
_client_factory = _default_client


def set_client_factory(factory) -> None:
    global _client_factory
    _client_factory = factory


def reset_client_factory() -> None:
    global _client_factory
    _client_factory = _default_client


@router.post("/outline", response_model=OutlineResponse)
def create_outline(req: OutlineRequest) -> OutlineResponse:
    if len(req.content) > _MAX_CONTENT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"content exceeds {_MAX_CONTENT_CHARS} chars; trim or split.",
        )

    log.debug(
        "outline request: source_type=%s language=%s content_chars=%d",
        req.source_type, req.language, len(req.content),
    )

    t0 = time.perf_counter()
    used_fallback = False
    used_model: str | None = None
    outline: OutlineDoc | None = None

    try:
        client = _client_factory()
        resp = client.chat_json(SYSTEM_PROMPT, build_user_message(req.content, req.language))
        used_model = resp.model
        try:
            obj = repair(resp.raw_content)
            outline = OutlineDoc.model_validate(obj)
        except (JsonRepairError, ValidationError) as exc:
            log.warning("LLM JSON unusable, using fallback: %s", exc)
            log.debug("LLM raw content (first 500 chars): %s", resp.raw_content[:500])
            used_fallback = True
    except LlmUnavailableError as exc:
        log.warning("LLM unavailable, using fallback: %s", exc)
        used_fallback = True

    if outline is None:
        outline = rule_based(req.content)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log.info(
        "outline done: sections=%d fallback=%s model=%s elapsed_ms=%d",
        len(outline.sections),
        used_fallback,
        used_model,
        elapsed_ms,
    )
    return OutlineResponse(
        outline=outline,
        used_fallback=used_fallback,
        used_model=used_model,
        elapsed_ms=elapsed_ms,
    )
