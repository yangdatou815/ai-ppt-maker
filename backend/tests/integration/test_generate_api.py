"""Integration tests for ``POST /api/generate``."""
from __future__ import annotations

import io

import pptx


def _outline_payload() -> dict:
    return {
        "title": "Q4 发布",
        "subtitle": "下一代产品 X",
        "language": "zh",
        "sections": [
            {
                "heading": "市场",
                "bullets": [
                    {"text": "增速放缓", "emphasis": True, "note": None},
                    {"text": "对手发力", "emphasis": False, "note": "重点关注"},
                ],
                "speaker_notes": "强调差异化",
                "image": None,
                "table": None,
                "layout_hint": None,
            },
            {
                "heading": "方案",
                "bullets": [{"text": "核心能力", "emphasis": False, "note": None}],
                "speaker_notes": None,
                "image": None,
                "table": None,
                "layout_hint": None,
            },
        ],
        "cover_meta": {"company": "ACME", "date": "2026-05"},
    }


def test_generate_returns_pptx_bytes(client):
    r = client.post(
        "/api/generate",
        json={"outline": _outline_payload(), "template": "executive-dark"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and ".pptx" in cd
    body = r.content
    assert body[:4] == b"PK\x03\x04", "should be a real .pptx zip"

    prs = pptx.Presentation(io.BytesIO(body))
    # cover + 2 sections + closing
    assert len(prs.slides) == 4


def test_generate_rejects_unknown_template(client):
    r = client.post(
        "/api/generate",
        json={"outline": _outline_payload(), "template": "no-such-template"},
    )
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_generate_rejects_malformed_outline(client):
    r = client.post(
        "/api/generate",
        json={"outline": {"title": "x"}, "template": "executive-dark"},  # missing sections
    )
    assert r.status_code == 422


def test_generate_works_for_all_shipped_templates(client):
    for name in ("executive-dark", "minimal-light", "tech-blue"):
        r = client.post(
            "/api/generate",
            json={"outline": _outline_payload(), "template": name},
        )
        assert r.status_code == 200, f"{name}: {r.text}"
        assert r.content[:4] == b"PK\x03\x04"
        assert r.headers.get("x-render-template") == name
