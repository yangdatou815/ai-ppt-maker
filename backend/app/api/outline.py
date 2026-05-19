"""Outline generation orchestrator: source -> LLM (with repair) -> fallback."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.outline.classify_fallback import DEFAULT_TEMPLATE, classify_heuristic
from app.outline.classify_prompts import (
    CLASSIFY_SYSTEM_PROMPT,
    build_classify_user_message,
)
from app.outline.fallback import rule_based
from app.outline.llm_client import LlmUnavailableError, OllamaClient
from app.outline.prompts import SYSTEM_PROMPT, build_user_message
from app.outline.repair import JsonRepairError, repair
from app.outline.summarizer import maybe_summarize
from app.schemas.classify import (
    ALLOWED_TEMPLATES,
    ClassifyTemplateRequest,
    ClassifyTemplateResponse,
)
from app.schemas.outline import OutlineDoc

log = logging.getLogger(__name__)
router = APIRouter()

_MAX_CONTENT_CHARS = 50_000


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
        req.source_type,
        req.language,
        len(req.content),
    )

    t0 = time.perf_counter()
    used_fallback = False
    used_model: str | None = None
    outline: OutlineDoc | None = None

    try:
        client = _client_factory()
        content_for_llm = maybe_summarize(req.content, client)
        resp = client.chat_json(SYSTEM_PROMPT, build_user_message(content_for_llm, req.language))
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


class AsyncOutlineResponse(BaseModel):
    job_id: str


@router.post("/outline/async", response_model=AsyncOutlineResponse)
def create_outline_async(req: OutlineRequest) -> AsyncOutlineResponse:
    """Submit outline generation as a background job. Poll GET /api/jobs/{job_id}."""
    if len(req.content) > _MAX_CONTENT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"content exceeds {_MAX_CONTENT_CHARS} chars; trim or split.",
        )

    from app.jobs.queue import submit_job

    def _run_outline(job):
        job.progress.stage = "summarize"
        job.progress.detail = "正在压缩长文本..."
        job.progress.percent = 10

        client = _client_factory()
        content_for_llm = maybe_summarize(req.content, client)

        job.progress.stage = "outline"
        job.progress.detail = "正在生成大纲..."
        job.progress.percent = 40

        used_fallback = False
        used_model = None
        outline = None

        try:
            resp = client.chat_json(
                SYSTEM_PROMPT, build_user_message(content_for_llm, req.language)
            )
            used_model = resp.model
            try:
                obj = repair(resp.raw_content)
                outline = OutlineDoc.model_validate(obj)
            except (JsonRepairError, ValidationError):
                used_fallback = True
        except LlmUnavailableError:
            used_fallback = True

        if outline is None:
            outline = rule_based(req.content)

        job.progress.stage = "done"
        job.progress.detail = "大纲生成完成"
        job.progress.percent = 100

        return {
            "outline": outline.model_dump(),
            "used_fallback": used_fallback,
            "used_model": used_model,
        }

    job_id = submit_job(_run_outline)
    return AsyncOutlineResponse(job_id=job_id)


@router.post("/classify-template", response_model=ClassifyTemplateResponse)
def classify_template(req: ClassifyTemplateRequest) -> ClassifyTemplateResponse:
    """Recommend the best slide template for the given source text.

    Mirrors the outline pipeline: try the LLM, repair JSON, validate the
    template against an allowlist, fall back to a deterministic keyword
    heuristic on any error so the endpoint never 5xx's. The
    ``used_fallback`` flag lets the UI surface a "guess" badge.
    """
    if len(req.content) > _MAX_CONTENT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"content exceeds {_MAX_CONTENT_CHARS} chars; trim or split.",
        )

    log.debug(
        "classify request: language=%s content_chars=%d",
        req.language,
        len(req.content),
    )

    t0 = time.perf_counter()
    used_fallback = False
    used_model: str | None = None
    template: str | None = None
    confidence: float = 0.0
    reason: str = ""

    try:
        client = _client_factory()
        resp = client.chat_json(
            CLASSIFY_SYSTEM_PROMPT,
            build_classify_user_message(req.content, req.language),
        )
        used_model = resp.model
        try:
            obj = repair(resp.raw_content)
            picked = str(obj.get("template", "")).strip()
            if picked not in ALLOWED_TEMPLATES:
                raise ValueError(f"LLM returned unknown template: {picked!r}")
            template = picked
            raw_conf = obj.get("confidence", 0.5)
            try:
                confidence = max(0.0, min(1.0, float(raw_conf)))
            except (TypeError, ValueError):
                confidence = 0.5
            raw_reason = obj.get("reason", "")
            reason = str(raw_reason).strip() or "LLM did not provide a reason."
        except (JsonRepairError, ValueError) as exc:
            log.warning("Classify JSON unusable, using heuristic: %s", exc)
            log.debug("Classify raw content (first 500 chars): %s", resp.raw_content[:500])
            used_fallback = True
    except LlmUnavailableError as exc:
        log.warning("LLM unavailable for classify, using heuristic: %s", exc)
        used_fallback = True

    if template is None:
        template, confidence, reason = classify_heuristic(req.content)
        if template not in ALLOWED_TEMPLATES:  # paranoia — heuristic is hard-coded
            template = DEFAULT_TEMPLATE

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log.info(
        "classify done: template=%s confidence=%.2f fallback=%s model=%s elapsed_ms=%d",
        template,
        confidence,
        used_fallback,
        used_model,
        elapsed_ms,
    )
    return ClassifyTemplateResponse(
        template=template,
        confidence=confidence,
        reason=reason,
        used_fallback=used_fallback,
        used_model=used_model,
        elapsed_ms=elapsed_ms,
    )
