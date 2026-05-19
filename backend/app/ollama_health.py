"""Probe the local Ollama daemon for the configured model.

``/api/healthz`` used to just echo ``settings.ollama_model`` back as if it
were a health indicator, which masked the case where the model name is set
but the model itself is not pulled — backend looks "fine" until the first
real LLM call 500s. This module gives healthz a real answer.

Design notes:

- Probe is best-effort: any network error / non-200 must return
  ``reachable=False`` without raising. healthz must stay cheap (<200ms) and
  never block on a flaky daemon.
- Use ``trust_env=False`` so the probe ignores corporate ``http_proxy`` that
  would otherwise mis-route 127.0.0.1 through an HTML-spewing gateway (see
  ``debugging.md`` — httpx + loopback + corporate proxy).
- "Model present" accepts any tag whose name shares the configured model's
  *base* (suffix ``-qN_K_M`` / ``-qN`` stripped). That way configuring
  ``qwen2.5:7b-instruct`` still reports healthy when only the quantised
  ``qwen2.5:7b-instruct-q4_K_M`` is pulled — same model family, just
  smaller. Matches the deploy.sh skip-if-present logic.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

_QUANT_SUFFIX = re.compile(r"-q[0-9].*$")
_PROBE_TIMEOUT_S = 1.5


@dataclass(frozen=True)
class OllamaHealth:
    reachable: bool
    model_present: bool
    matched: str | None  # actual tag in ollama, if any base match

    def to_dict(self) -> dict:
        return {
            "reachable": self.reachable,
            "model_present": self.model_present,
            "matched": self.matched,
        }


def _base(tag: str) -> str:
    """Strip a trailing ``-qN`` / ``-qN_K_M`` suffix from an ollama tag."""
    return _QUANT_SUFFIX.sub("", tag)


def _match_model(configured: str, available: Iterable[str]) -> str | None:
    """Return the first tag in ``available`` whose base matches ``configured``.

    Exact match wins; otherwise any tag whose base equals the configured
    model's base counts (e.g. configured=``qwen2.5:7b-instruct`` matches
    available=``qwen2.5:7b-instruct-q4_K_M``).
    """
    configured_base = _base(configured)
    exact = None
    family = None
    for tag in available:
        if tag == configured:
            exact = tag
            break
        if _base(tag) == configured_base and family is None:
            family = tag
    return exact or family


def probe_ollama(base_url: str, model: str) -> OllamaHealth:
    """Best-effort check of ``GET {base_url}/api/tags``.

    Always returns; never raises. Logs at DEBUG only — repeated healthz
    polling must not flood WARN logs.
    """
    url = base_url.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(trust_env=False, timeout=_PROBE_TIMEOUT_S) as cli:
            resp = cli.get(url)
        if resp.status_code != 200:
            log.debug("ollama probe %s -> %s", url, resp.status_code)
            return OllamaHealth(reachable=False, model_present=False, matched=None)
        payload = resp.json()
    except Exception as exc:  # network, JSON, anything
        log.debug("ollama probe %s failed: %s", url, exc)
        return OllamaHealth(reachable=False, model_present=False, matched=None)

    tags = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
    matched = _match_model(model, tags)
    return OllamaHealth(reachable=True, model_present=matched is not None, matched=matched)
