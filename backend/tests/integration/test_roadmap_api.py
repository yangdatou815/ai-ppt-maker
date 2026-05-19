"""Integration tests for /api/roadmap."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.roadmap import _load_roadmap_cached, load_roadmap
from app.main import app


@pytest.fixture(autouse=True)
def _clear_cache():
    _load_roadmap_cached.cache_clear()
    yield
    _load_roadmap_cached.cache_clear()


def test_get_roadmap_returns_phases_and_stats():
    with TestClient(app) as client:
        r = client.get("/api/roadmap")
    assert r.status_code == 200
    body = r.json()
    assert "phases" in body
    assert "stats" in body
    assert isinstance(body["phases"], list)
    assert len(body["phases"]) > 0
    # Stats shape
    s = body["stats"]
    assert s["total"] == s["done"] + s["in_progress"] + s["planned"]
    assert 0.0 <= s["done_pct"] <= 100.0


def test_get_roadmap_each_phase_has_milestones_with_items():
    with TestClient(app) as client:
        r = client.get("/api/roadmap")
    body = r.json()
    for phase in body["phases"]:
        assert phase["id"]
        assert phase["name"]
        assert isinstance(phase["milestones"], list)
        for ms in phase["milestones"]:
            assert ms["id"]
            assert ms["name"]
            for item in ms["items"]:
                assert item["name"]
                assert item["status"] in ("done", "in-progress", "planned")


def test_load_roadmap_rejects_invalid_status(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "phases:\n"
        "  - id: x\n"
        "    name: X\n"
        "    milestones:\n"
        "      - id: m\n"
        "        name: M\n"
        "        items:\n"
        "          - { name: a, status: bogus }\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_roadmap(bad)


def test_load_roadmap_minimal_yaml(tmp_path: Path):
    f = tmp_path / "min.yaml"
    f.write_text(
        "phases:\n"
        "  - id: p1\n"
        "    name: Phase 1\n"
        "    milestones:\n"
        "      - id: m1\n"
        "        name: First\n"
        "        items:\n"
        "          - { name: do thing, status: done }\n"
        "          - { name: maybe later, status: planned }\n",
        encoding="utf-8",
    )
    doc = load_roadmap(f)
    assert doc.stats.total == 2
    assert doc.stats.done == 1
    assert doc.stats.planned == 1
    assert doc.stats.done_pct == 50.0
