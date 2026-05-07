"""Centralised logging setup with per-module level overrides.

Design (architecture §7 — Observability):

    - Single entry point ``setup_logging`` called once from ``app.main``.
    - Root level controlled by ``LOG_LEVEL`` env (``DEBUG`` / ``INFO`` /
      ``WARNING`` / ``ERROR`` / ``CRITICAL``); default ``INFO``.
    - Per-logger overrides via ``LOG_LEVEL_OVERRIDES`` env, comma-separated
      ``logger.name=LEVEL`` pairs, e.g.::

          LOG_LEVEL=INFO LOG_LEVEL_OVERRIDES="app.outline=DEBUG,httpx=WARNING"

      so an operator can crank a single subsystem to DEBUG without flooding
      the rest. This is the "log switch" the PRD calls for.
    - Format pinned to ``%(asctime)s %(levelname)-7s %(name)s :: %(message)s``
      (sortable timestamp, fixed-width level for grep/awk).
    - Idempotent: calling twice does not duplicate handlers — useful for
      tests and uvicorn's reload mode.
    - Aligns uvicorn's own loggers with the project level so request logs and
      app logs share one switch.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterable

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_VALID = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Loggers that should follow the project root level by default. Listed
# explicitly so we don't silently mute or amplify third-party logs.
_FOLLOW_ROOT: Iterable[str] = ("uvicorn", "uvicorn.error", "uvicorn.access")


def _coerce(level: str | int, default: int = logging.INFO) -> int:
    """Return a numeric log level; tolerate junk so a typo never crashes startup."""
    if isinstance(level, int):
        return level
    name = (level or "").strip().upper()
    if name in _VALID:
        return getattr(logging, name)
    return default


def _parse_overrides(raw: str | None) -> dict[str, int]:
    """Parse ``a=DEBUG,b.c=WARNING`` into ``{"a": 10, "b.c": 30}``.

    Silently drops malformed entries — observability tooling should never
    take the app down.
    """
    out: dict[str, int] = {}
    if not raw:
        return out
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        name, _, level = pair.strip().partition("=")
        name = name.strip()
        if not name:
            continue
        out[name] = _coerce(level)
    return out


def setup_logging(
    level: str | int = "INFO",
    overrides: dict[str, int] | None = None,
) -> None:
    """Configure root + project loggers idempotently.

    Args:
        level: root level (string name or numeric).
        overrides: explicit per-logger overrides; if ``None`` reads
            ``LOG_LEVEL_OVERRIDES`` from env.
    """
    root_level = _coerce(level)
    if overrides is None:
        overrides = _parse_overrides(os.environ.get("LOG_LEVEL_OVERRIDES"))

    # Handler must be at least as verbose as the most verbose logger,
    # otherwise a logger set to DEBUG would still be filtered at the handler.
    handler_level = min([root_level, *overrides.values()]) if overrides else root_level

    root = logging.getLogger()
    root.setLevel(root_level)

    # Idempotent handler setup — replace any handler we previously installed.
    handler: logging.Handler | None = next(
        (h for h in root.handlers if getattr(h, "_apm_managed", False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler._apm_managed = True  # type: ignore[attr-defined]
        root.addHandler(handler)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
    handler.setLevel(handler_level)

    # Realign uvicorn loggers (they install their own handlers; mute those
    # to avoid duplicate lines, then let our root handler render them).
    for name in _FOLLOW_ROOT:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.setLevel(root_level)
        lg.propagate = True

    for name, lvl in overrides.items():
        logging.getLogger(name).setLevel(lvl)
