"""Test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.api import templates as templates_api
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    templates_api.reset_cache()
    app = create_app()
    return TestClient(app)
