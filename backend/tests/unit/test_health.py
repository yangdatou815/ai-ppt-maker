from app.ollama_health import OllamaHealth


def test_healthz_reports_ollama_status(client, monkeypatch):
    # Pin the probe so the test doesn't depend on a real daemon.
    monkeypatch.setattr(
        "app.main.probe_ollama",
        lambda _url, _model: OllamaHealth(
            reachable=True, model_present=True, matched="qwen2.5:7b-instruct-q4_K_M"
        ),
    )
    r = client.get("/api/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "version" in body
    assert body["ollama"] == {
        "reachable": True,
        "model_present": True,
        "matched": "qwen2.5:7b-instruct-q4_K_M",
    }


def test_healthz_unreachable_ollama(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.probe_ollama",
        lambda _url, _model: OllamaHealth(reachable=False, model_present=False, matched=None),
    )
    r = client.get("/api/healthz")
    assert r.status_code == 200
    body = r.json()
    # backend itself is "ok"; only the LLM dependency is degraded
    assert body["ok"] is True
    assert body["ollama"]["reachable"] is False
    assert body["ollama"]["model_present"] is False
    assert body["ollama"]["matched"] is None
