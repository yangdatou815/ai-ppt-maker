"""Rule-based fallback outline generator.

Used when the LLM is unavailable or returns un-repairable output (TD-2).
Splits source text by Markdown headings (##/###) or blank-line paragraphs,
keeping the user productive even without Ollama.
"""
from __future__ import annotations

import logging
import re

from app.schemas.outline import Bullet, OutlineDoc, Section

log = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _detect_language(text: str) -> str:
    # crude but enough for fallback: count CJK chars vs ASCII letters
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return "zh" if cjk * 2 >= sum(1 for c in text if c.isalpha()) else "en"


def _shorten(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Return [(heading, body), ...] using Markdown headings if present, else paragraphs."""
    matches = list(_HEADING_RE.finditer(text))
    if matches:
        sections: list[tuple[str, str]] = []
        for i, m in enumerate(matches):
            heading = m.group(2).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            sections.append((heading, body))
        return sections

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [("Overview", text.strip() or "No content provided.")]
    sections = []
    for i, p in enumerate(paragraphs[:8], start=1):
        first_line = p.splitlines()[0].strip()
        heading = _shorten(first_line, 24) or f"Part {i}"
        sections.append((heading, p))
    return sections


def _bullets_from_body(body: str, language: str) -> list[Bullet]:
    bullets: list[Bullet] = []
    line_items = [
        m.group(1).strip()
        for m in re.finditer(r"^[\s]*[-*•·]\s+(.+?)\s*$", body, re.MULTILINE)
    ]
    if line_items:
        for it in line_items[:5]:
            bullets.append(Bullet(text=_shorten(it, 40)))
    else:
        sentences = re.split(r"(?<=[。！？!?.])\s+|\n+", body)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sent in sentences[:5]:
            bullets.append(Bullet(text=_shorten(sent, 40)))
    if not bullets:
        bullets.append(Bullet(text="(no detail)" if language == "en" else "（无细节）"))
    return bullets


def rule_based(content: str, *, fallback_title: str | None = None) -> OutlineDoc:
    text = (content or "").strip()
    language = _detect_language(text)
    sections_raw = _split_into_sections(text)

    title = fallback_title or _shorten(sections_raw[0][0], 30)
    subtitle = (
        "Auto-generated outline (LLM unavailable)"
        if language == "en"
        else "自动生成的大纲（LLM 暂不可用）"
    )

    sections: list[Section] = []
    for heading, body in sections_raw[:10]:
        sections.append(
            Section(
                heading=_shorten(heading, 24),
                bullets=_bullets_from_body(body, language),
                speaker_notes=_shorten(body.replace("\n", " "), 200),
                layout_hint="content-bullets",
            )
        )

    log.debug(
        "fallback: lang=%s input_chars=%d sections_raw=%d sections_kept=%d",
        language, len(text), len(sections_raw), len(sections),
    )
    return OutlineDoc(
        title=title or ("Untitled" if language == "en" else "未命名"),
        subtitle=subtitle,
        language=language,  # type: ignore[arg-type]
        sections=sections,
    )
