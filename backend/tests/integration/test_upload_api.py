"""Integration tests for POST /api/upload."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _png_1x1() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.fixture
def upload_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Force workspace to a tmp dir so we don't pollute the user's real one.
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    # Bust the cached settings singleton.
    import app.config as cfg

    cfg._settings = None
    yield TestClient(create_app())
    cfg._settings = None


def test_upload_happy_path_persists_file(upload_client: TestClient, tmp_path: Path):
    payload = _png_1x1()
    r = upload_client.post(
        "/api/upload",
        files={"file": ("pic.png", payload, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bytes"] == len(payload)
    assert body["content_type"] == "image/png"
    assert body["file_id"].endswith(".png")

    # File must actually be on disk under <workspace>/uploads/
    uploads = get_settings().workspace_dir / "uploads"
    assert (uploads / body["file_id"]).read_bytes() == payload


def test_upload_rejects_unsupported_mime(upload_client: TestClient):
    r = upload_client.post(
        "/api/upload",
        files={"file": ("doc.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert r.status_code == 415
    assert "unsupported content-type" in r.json()["detail"]


def test_upload_rejects_oversize(upload_client: TestClient):
    # max_upload_mb is 1 in fixture; send 2 MB.
    big = b"\x00" * (2 * 1024 * 1024)
    r = upload_client.post(
        "/api/upload",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413


def test_upload_rejects_empty_file(upload_client: TestClient):
    r = upload_client.post(
        "/api/upload",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert r.status_code == 400
