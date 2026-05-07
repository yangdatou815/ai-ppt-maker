"""Integration tests for /api/outline with stub Ollama client."""
import json

import pytest

from app.api import outline as outline_api
from app.outline.llm_client import LlmResponse, LlmUnavailableError


class StubClient:
    """Implements the OllamaClient.chat_json contract."""

    def __init__(self, content: str, model: str = "stub-7b"):
        self._content = content
        self._model = model

    def chat_json(self, system: str, user: str) -> LlmResponse:
        return LlmResponse(raw_content=self._content, model=self._model)


class FailingClient:
    def chat_json(self, system: str, user: str) -> LlmResponse:
        raise LlmUnavailableError("boom")


@pytest.fixture(autouse=True)
def _reset_factory():
    yield
    outline_api.reset_client_factory()


def _good_outline_json() -> str:
    return json.dumps(
        {
            "title": "Q4 发布",
            "subtitle": "下一代产品 X",
            "language": "zh",
            "sections": [
                {
                    "heading": "市场",
                    "bullets": [
                        {"text": "TAM 100B", "note": None, "emphasis": True},
                        {"text": "增速 40%", "note": None, "emphasis": False},
                        {"text": "竞品集中", "note": None, "emphasis": False},
                    ],
                    "speaker_notes": "市场快速增长。",
                    "layout_hint": "content-bullets",
                },
                {
                    "heading": "产品",
                    "bullets": [
                        {"text": "更快", "note": None, "emphasis": False},
                        {"text": "更稳", "note": None, "emphasis": False},
                        {"text": "更省", "note": None, "emphasis": False},
                    ],
                    "speaker_notes": "三大改进。",
                    "layout_hint": None,
                },
            ],
            "cover_meta": {},
        },
        ensure_ascii=False,
    )


def test_happy_path_uses_llm(client):
    outline_api.set_client_factory(lambda: StubClient(_good_outline_json()))
    r = client.post("/api/outline", json={"content": "随便一段稿子"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["used_fallback"] is False
    assert body["used_model"] == "stub-7b"
    assert body["outline"]["title"] == "Q4 发布"
    assert len(body["outline"]["sections"]) == 2


def test_fenced_json_repaired(client):
    fenced = "```json\n" + _good_outline_json() + "\n```"
    outline_api.set_client_factory(lambda: StubClient(fenced))
    r = client.post("/api/outline", json={"content": "x"})
    assert r.status_code == 200
    assert r.json()["used_fallback"] is False


def test_garbage_falls_back(client):
    outline_api.set_client_factory(lambda: StubClient("totally not json"))
    r = client.post("/api/outline", json={"content": "## Foo\n- a\n- b"})
    assert r.status_code == 200
    body = r.json()
    assert body["used_fallback"] is True
    assert body["outline"]["sections"]


def test_llm_down_falls_back(client):
    outline_api.set_client_factory(lambda: FailingClient())
    r = client.post("/api/outline", json={"content": "Hello world"})
    assert r.status_code == 200
    body = r.json()
    assert body["used_fallback"] is True
    assert body["used_model"] is None


def test_oversize_rejected(client):
    big = "a" * 30000
    r = client.post("/api/outline", json={"content": big})
    assert r.status_code == 413


def test_empty_rejected(client):
    r = client.post("/api/outline", json={"content": ""})
    assert r.status_code == 422  # pydantic min_length=1


def test_validation_failure_falls_back(client):
    # LLM returns syntactically valid JSON, but missing required fields → fallback
    bad = json.dumps({"foo": "bar"})
    outline_api.set_client_factory(lambda: StubClient(bad))
    r = client.post("/api/outline", json={"content": "Hello"})
    assert r.status_code == 200
    assert r.json()["used_fallback"] is True
