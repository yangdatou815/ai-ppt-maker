EXPECTED_NAMES = {"executive-dark", "minimal-light", "tech-blue"}


def test_templates_list_returns_three(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    names = {t["name"] for t in items}
    assert names == EXPECTED_NAMES


def test_templates_list_payload_shape(client):
    r = client.get("/api/templates")
    items = r.json()
    for t in items:
        assert t["display_name"]
        assert t["description"]
        assert isinstance(t["tags"], list) and t["tags"]
        assert isinstance(t["theme"], dict) and "primary" in t["theme"]
        assert isinstance(t["fonts"], dict) and "heading" in t["fonts"]
        assert isinstance(t["has_master"], bool)


def test_template_detail(client):
    r = client.get("/api/templates/executive-dark")
    assert r.status_code == 200
    assert r.json()["name"] == "executive-dark"


def test_template_detail_404(client):
    r = client.get("/api/templates/does-not-exist")
    assert r.status_code == 404


def test_template_thumbnail_served_for_known_template(client):
    r = client.get("/api/templates/executive-dark/thumbnail.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    body = r.content
    # PNG magic number — guards against accidentally serving an HTML error.
    assert body[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(body) > 500


def test_template_thumbnail_listed_in_api(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    items = {t["name"]: t for t in r.json()}
    # Every shipped template should expose a thumbnail URL now.
    for name in ("executive-dark", "minimal-light", "tech-blue"):
        assert items[name]["thumbnail_url"] == f"/api/templates/{name}/thumbnail.png"


def test_template_thumbnail_404_for_unknown_template(client):
    r = client.get("/api/templates/does-not-exist/thumbnail.png")
    assert r.status_code == 404


def test_template_thumbnail_rejects_path_traversal(client):
    # The route handler allowlists template names against the live registry,
    # so ``..`` and other non-template names cannot reach FileResponse. If
    # the request falls through to the SPA catch-all that is fine — what
    # must NEVER happen is that a PNG outside the templates registry is
    # served back.
    r = client.get("/api/templates/..%2Fapp/thumbnail.png")
    if r.status_code == 200:
        assert r.headers.get("content-type") != "image/png", "path traversal must not return a PNG"


def test_outline_falls_back_when_llm_down(client, monkeypatch):
    # In unit context (no Ollama), real /api/outline should still 200 via fallback.
    # The LlmUnavailableError → rule_based path is exercised in tests/integration.
    # Here we just assert the route is wired.
    from app.api import outline as outline_api
    from app.outline.llm_client import LlmUnavailableError

    class _Down:
        def chat_json(self, system, user):
            raise LlmUnavailableError("offline for unit test")

    outline_api.set_client_factory(lambda: _Down())
    try:
        r = client.post("/api/outline", json={"source_type": "text", "content": "hi"})
        assert r.status_code == 200
        body = r.json()
        assert body["used_fallback"] is True
    finally:
        outline_api.reset_client_factory()


def test_jobs_stub_404(client):
    r = client.get("/api/jobs/nope")
    assert r.status_code == 404
