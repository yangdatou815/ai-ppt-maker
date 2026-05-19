"""Integration tests for the runtime debug toggle + log SSE."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient


def test_debug_default_state_is_disabled(client: TestClient):
    r = client.get("/api/debug")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    # Whatever the configured baseline is, must be a valid level name.
    assert body["level"] in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def test_debug_toggle_round_trip(client: TestClient):
    r = client.post("/api/debug", json={"enabled": True})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["level"] == "DEBUG"

    # Root logger really moved to DEBUG (otherwise 'enabled' is a lie).
    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG

    r = client.post("/api/debug", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    # Root must be raised back above DEBUG (whatever the configured baseline
    # is — INFO in tests, ERROR in prod default — both pass).
    assert logging.getLogger().getEffectiveLevel() > logging.DEBUG


def test_debug_buffer_captures_records_when_enabled(client: TestClient):
    # SSE endpoint can't be exercised easily through TestClient.stream
    # (the response never closes naturally — heartbeat keeps it open),
    # so we test the underlying contract instead: when debug is on, log
    # records land in the in-memory ring buffer that SSE replays from.
    from app.api.debug import _buffer

    client.post("/api/debug", json={"enabled": True})
    try:
        marker = "test-debug-marker-7f3"
        logging.getLogger("test.debug").info(marker)
        assert any(marker in r["msg"] for r in _buffer.buffer)
    finally:
        client.post("/api/debug", json={"enabled": False})

    # And buffer is cleared when debug is turned off.
    assert len(_buffer.buffer) == 0


def test_debug_logs_stream_endpoint_route_exists(client: TestClient):
    # Don't actually open the long-lived SSE response in TestClient
    # (Starlette's sync TestClient doesn't unblock cleanly on streamed
    # async generators that never EOF). Instead verify the route is
    # registered by inspecting the OpenAPI schema — that's what users see.
    schema = client.get("/openapi.json").json()
    assert "/api/debug/logs/stream" in schema["paths"]
    assert "get" in schema["paths"]["/api/debug/logs/stream"]
