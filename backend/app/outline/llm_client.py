"""Ollama HTTP client for outline generation.

Calls POST /api/chat with format="json", strict timeout, and a single retry.
The orchestrator (api/outline.py) handles repair + fallback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)


class LlmUnavailableError(RuntimeError):
    """Ollama unreachable, model missing, or HTTP error after retry."""


@dataclass
class LlmResponse:
    raw_content: str
    model: str
    eval_count: int | None = None
    eval_duration_ns: int | None = None


class OllamaClient:
    """Thin wrapper over Ollama's /api/chat. One retry on transient failures."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: int = 120,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self._client = client  # injected for tests; we own lifecycle when None

    def _new_client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_s)

    def chat_json(self, system: str, user: str) -> LlmResponse:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        url = f"{self.base_url}/api/chat"

        log.debug(
            "ollama call: url=%s model=%s timeout=%ss system_chars=%d user_chars=%d",
            url, self.model, self.timeout_s, len(system), len(user),
        )

        last_err: Exception | None = None
        for attempt in (1, 2):
            client = self._client or self._new_client()
            owns = self._client is None
            try:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                msg = (data.get("message") or {}).get("content", "")
                if not isinstance(msg, str) or not msg.strip():
                    raise LlmUnavailableError("Ollama returned empty content")
                eval_count = data.get("eval_count")
                eval_duration_ns = data.get("eval_duration")
                log.debug(
                    "ollama ok: attempt=%d model=%s eval_count=%s eval_duration_ms=%s content_chars=%d",
                    attempt, data.get("model", self.model), eval_count,
                    None if eval_duration_ns is None else eval_duration_ns // 1_000_000,
                    len(msg),
                )
                return LlmResponse(
                    raw_content=msg,
                    model=data.get("model", self.model),
                    eval_count=eval_count,
                    eval_duration_ns=eval_duration_ns,
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_err = exc
                log.warning("Ollama call attempt %d failed: %s", attempt, exc)
            finally:
                if owns:
                    client.close()
        raise LlmUnavailableError(f"Ollama unavailable after retry: {last_err}")
