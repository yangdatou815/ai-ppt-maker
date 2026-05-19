"""Tests for the Ollama daemon probe used by /api/healthz."""

from __future__ import annotations

import httpx
import pytest

from app.ollama_health import OllamaHealth, _base, _match_model, probe_ollama


class TestBase:
    @pytest.mark.parametrize(
        "tag,expected",
        [
            ("qwen2.5:7b-instruct", "qwen2.5:7b-instruct"),
            ("qwen2.5:7b-instruct-q4_K_M", "qwen2.5:7b-instruct"),
            ("qwen2.5:7b-instruct-q8_0", "qwen2.5:7b-instruct"),
            ("llama3.1:8b-instruct-q4_0", "llama3.1:8b-instruct"),
            ("llama3.1:8b", "llama3.1:8b"),
        ],
    )
    def test_strips_quant_suffix(self, tag: str, expected: str) -> None:
        assert _base(tag) == expected


class TestMatchModel:
    def test_exact_wins(self) -> None:
        assert _match_model("qwen2.5:7b-instruct", ["qwen2.5:7b-instruct"]) == "qwen2.5:7b-instruct"

    def test_quant_variant_matches_base(self) -> None:
        # Configured the base tag, only the quantised variant is pulled.
        assert (
            _match_model("qwen2.5:7b-instruct", ["qwen2.5:7b-instruct-q4_K_M"])
            == "qwen2.5:7b-instruct-q4_K_M"
        )

    def test_base_matches_when_configured_is_quant(self) -> None:
        # Reverse direction: configured quant, only base is pulled.
        assert (
            _match_model("qwen2.5:7b-instruct-q4_K_M", ["qwen2.5:7b-instruct"])
            == "qwen2.5:7b-instruct"
        )

    def test_no_match(self) -> None:
        assert _match_model("qwen2.5:7b-instruct", ["llama3.1:8b"]) is None

    def test_empty(self) -> None:
        assert _match_model("qwen2.5:7b-instruct", []) is None

    def test_exact_preferred_over_family(self) -> None:
        result = _match_model(
            "qwen2.5:7b-instruct",
            ["qwen2.5:7b-instruct-q4_K_M", "qwen2.5:7b-instruct"],
        )
        assert result == "qwen2.5:7b-instruct"


def _mock_transport(payload: dict, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)


def _install_mock_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    """Patch httpx.Client used inside app.ollama_health to inject ``transport``.

    The probe calls ``httpx.Client(trust_env=False, timeout=...)`` — we
    capture those kwargs, drop ``trust_env`` (incompatible with explicit
    transports in httpx), and hand back a Client built on the mock.
    Use the real Client class captured *before* the patch to avoid recursion.
    """
    real_client_cls = httpx.Client

    def factory(*args, **kwargs):
        kwargs.pop("trust_env", None)
        return real_client_cls(transport=transport, **kwargs)

    monkeypatch.setattr("app.ollama_health.httpx.Client", factory)


class TestProbeOllama:
    def test_reachable_and_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {"models": [{"name": "qwen2.5:7b-instruct-q4_K_M"}]}
        _install_mock_client(monkeypatch, _mock_transport(payload))
        result = probe_ollama("http://127.0.0.1:11434", "qwen2.5:7b-instruct")
        assert result == OllamaHealth(
            reachable=True, model_present=True, matched="qwen2.5:7b-instruct-q4_K_M"
        )

    def test_reachable_but_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {"models": [{"name": "llama3.1:8b"}]}
        _install_mock_client(monkeypatch, _mock_transport(payload))
        result = probe_ollama("http://127.0.0.1:11434", "qwen2.5:7b-instruct")
        assert result.reachable is True
        assert result.model_present is False
        assert result.matched is None

    def test_empty_registry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mock_client(monkeypatch, _mock_transport({"models": []}))
        result = probe_ollama("http://127.0.0.1:11434", "qwen2.5:7b-instruct")
        assert result.reachable is True
        assert result.model_present is False
        assert result.matched is None

    def test_non_200_returns_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mock_client(monkeypatch, _mock_transport({}, status=503))
        result = probe_ollama("http://127.0.0.1:11434", "qwen2.5:7b-instruct")
        assert result == OllamaHealth(reachable=False, model_present=False, matched=None)

    def test_connection_error_is_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raising_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("nope", request=request)

        _install_mock_client(monkeypatch, httpx.MockTransport(raising_handler))
        result = probe_ollama("http://127.0.0.1:11434", "qwen2.5:7b-instruct")
        assert result == OllamaHealth(reachable=False, model_present=False, matched=None)
