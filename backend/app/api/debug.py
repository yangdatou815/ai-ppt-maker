"""Runtime debug toggle + log streaming.

Default operation runs the app at ``ERROR`` level so steady-state requests
don't pay the cost of formatting and emitting INFO log lines on every hop.
When the operator flips the toggle on (from the UI or a curl), we:

- Lower the root logger and our managed handler down to DEBUG.
- Attach a small in-memory ring buffer that captures every record so the
  frontend can replay recent history when the log panel opens.
- Allow Server-Sent-Events clients to subscribe and receive each new
  record as it happens, without polling.

Flipping back off restores the prior level and detaches the buffer
handler — no permanent overhead for production-style runs.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import deque
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.logging_setup import setup_logging

log = logging.getLogger(__name__)
router = APIRouter()


class _BufferHandler(logging.Handler):
    """Logging handler that fans every record out to (a) a fixed-size ring
    buffer for replay on connect and (b) every live asyncio queue.

    We intentionally keep this synchronous — `logging.Handler.emit` is
    called from arbitrary threads (uvicorn's request loop, background
    workers) and converting to async here would deadlock.  Instead we use
    `loop.call_soon_threadsafe` to hand off to each subscriber's queue.
    """

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self.buffer: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember which loop the SSE endpoint is running on."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - tested via integration
        try:
            payload = {
                "ts": record.created,
                "level": record.levelname,
                "name": record.name,
                "msg": record.getMessage(),
            }
        except Exception:
            return
        self.buffer.append(payload)
        if self._loop is None:
            return
        for q in list(self._subscribers):
            # Drop on slow consumer rather than blocking the logging path.
            self._loop.call_soon_threadsafe(_offer, q, payload)


def _offer(q: asyncio.Queue[dict[str, Any]], payload: dict[str, Any]) -> None:
    with contextlib.suppress(asyncio.QueueFull):
        q.put_nowait(payload)


_buffer = _BufferHandler()
_state: dict[str, Any] = {"enabled": False, "level": "ERROR"}


def _attach_buffer() -> None:
    root = logging.getLogger()
    if _buffer not in root.handlers:
        root.addHandler(_buffer)


def _detach_buffer() -> None:
    root = logging.getLogger()
    if _buffer in root.handlers:
        root.removeHandler(_buffer)
    _buffer.buffer.clear()


def _apply(enabled: bool) -> None:
    """Switch logging configuration to match the requested state."""
    settings = get_settings()
    if enabled:
        # DEBUG everywhere our code lives; keep noisy third-party libs at
        # WARNING so we get our own diagnostics without httpx/asyncio chatter.
        setup_logging(
            level="DEBUG",
            overrides={
                "httpx": logging.WARNING,
                "httpcore": logging.WARNING,
                "asyncio": logging.WARNING,
            },
        )
        _buffer.setLevel(logging.DEBUG)
        _attach_buffer()
        _state.update(enabled=True, level="DEBUG")
        log.info("debug mode ENABLED via /api/debug")
    else:
        # Restore configured baseline (defaults to ERROR per settings).
        setup_logging(level=settings.log_level)
        _detach_buffer()
        _state.update(enabled=False, level=settings.log_level.upper())


class DebugState(BaseModel):
    enabled: bool
    level: str
    buffered: int


class DebugUpdate(BaseModel):
    enabled: bool


@router.get("/debug")
def get_debug() -> DebugState:
    return DebugState(
        enabled=_state["enabled"],
        level=_state["level"],
        buffered=len(_buffer.buffer),
    )


@router.post("/debug")
def set_debug(req: DebugUpdate) -> DebugState:
    _apply(req.enabled)
    return DebugState(
        enabled=_state["enabled"],
        level=_state["level"],
        buffered=len(_buffer.buffer),
    )


async def _event_stream() -> Any:
    # Bind the running loop so the (possibly cross-thread) handler knows
    # where to send records.
    _buffer.bind_loop(asyncio.get_running_loop())

    # Replay the recent history first — operators usually open the panel
    # *because* something just happened, so the last 500 lines are the
    # interesting context.
    for line in list(_buffer.buffer):
        yield f"data: {json.dumps(line)}\n\n"

    q = _buffer.subscribe()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=15.0)
                yield f"data: {json.dumps(payload)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat keeps proxies / uvicorn from killing the
                # connection on long idle periods.
                yield f": ping {int(time.time())}\n\n"
    finally:
        _buffer.unsubscribe(q)


@router.get("/debug/logs/stream")
def stream_logs() -> StreamingResponse:
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables nginx response buffering
        },
    )
