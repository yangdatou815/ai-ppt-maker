"""Robust JSON repair for LLM outputs.

LLMs often wrap JSON in ```json fences, prepend "Sure, here is...", or leave
trailing commas. This module attempts progressively looser parsing strategies.
"""
from __future__ import annotations

import contextlib
import json
import logging
import re

log = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class JsonRepairError(ValueError):
    """Raised when no parsing strategy succeeded."""


def _strip_fence(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def _extract_first_object(s: str) -> str:
    """Find the first balanced {...} block in a string (handles surrounding prose)."""
    start = s.find("{")
    if start < 0:
        raise JsonRepairError("no '{' in payload")
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(s[start:], start=start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    raise JsonRepairError("unbalanced braces")


def _drop_trailing_commas(s: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", s)


def repair(raw: str) -> dict:
    """Best-effort: parse `raw` as JSON, return dict.

    Raises JsonRepairError if every strategy fails.
    """
    if not isinstance(raw, str):
        raise JsonRepairError(f"expected str, got {type(raw).__name__}")

    candidates: list[str] = []
    s = raw.strip()
    candidates.append(s)
    candidates.append(_strip_fence(s))
    with contextlib.suppress(JsonRepairError):
        candidates.append(_extract_first_object(s))
    candidates.append(_drop_trailing_commas(_strip_fence(s)))
    with contextlib.suppress(JsonRepairError):
        candidates.append(_drop_trailing_commas(_extract_first_object(s)))

    last_err: Exception | None = None
    for idx, c in enumerate(candidates):
        if not c:
            continue
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                log.debug(
                    "repair ok: strategy=%d input_chars=%d candidate_chars=%d keys=%s",
                    idx, len(raw), len(c), sorted(obj.keys())[:8],
                )
                return obj
            last_err = ValueError(f"top-level not an object: {type(obj).__name__}")
        except json.JSONDecodeError as e:
            last_err = e
            continue
    log.debug("repair failed: input_chars=%d last_err=%s", len(raw), last_err)
    raise JsonRepairError(f"all strategies failed: {last_err}")
