"""Tests for app.logging_setup — the operator-facing log switch."""
from __future__ import annotations

import logging

import pytest

from app.logging_setup import _coerce, _parse_overrides, setup_logging


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Each test gets a clean root logger; restore on teardown."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    root.handlers = saved_handlers
    root.setLevel(saved_level)


def test_coerce_accepts_known_names():
    assert _coerce("DEBUG") == logging.DEBUG
    assert _coerce("info") == logging.INFO
    assert _coerce("Warning") == logging.WARNING
    assert _coerce(logging.ERROR) == logging.ERROR


def test_coerce_falls_back_on_garbage():
    assert _coerce("LOUD") == logging.INFO
    assert _coerce(None) == logging.INFO  # type: ignore[arg-type]
    assert _coerce("") == logging.INFO


def test_parse_overrides_happy_path():
    out = _parse_overrides("app.outline=DEBUG,httpx=WARNING")
    assert out == {"app.outline": logging.DEBUG, "httpx": logging.WARNING}


def test_parse_overrides_tolerates_malformed():
    out = _parse_overrides("=DEBUG, app.x=INFO ,broken,, app.y=BOGUS")
    # broken pair dropped; "BOGUS" coerced to INFO; whitespace tolerated
    assert out == {"app.x": logging.INFO, "app.y": logging.INFO}


def test_setup_logging_sets_root_and_handler_level():
    setup_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    managed = [h for h in root.handlers if getattr(h, "_apm_managed", False)]
    assert len(managed) == 1
    assert managed[0].level == logging.DEBUG


def test_setup_logging_is_idempotent():
    setup_logging("INFO")
    setup_logging("WARNING")
    setup_logging("ERROR")
    root = logging.getLogger()
    managed = [h for h in root.handlers if getattr(h, "_apm_managed", False)]
    assert len(managed) == 1
    assert root.level == logging.ERROR


def test_setup_logging_applies_overrides():
    setup_logging("INFO", overrides={"app.outline": logging.DEBUG, "httpx": logging.ERROR})
    assert logging.getLogger("app.outline").level == logging.DEBUG
    assert logging.getLogger("httpx").level == logging.ERROR


def test_setup_logging_realigns_uvicorn_loggers():
    setup_logging("WARNING")
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        assert lg.level == logging.WARNING
        assert lg.handlers == []  # cleared so root handler renders
        assert lg.propagate is True


def test_handler_level_drops_to_match_most_verbose_override():
    """If root=INFO but an override is DEBUG, the handler must allow DEBUG
    through — otherwise the override is a no-op (regression test)."""
    setup_logging("INFO", overrides={"app.outline": logging.DEBUG})
    root = logging.getLogger()
    managed = [h for h in root.handlers if getattr(h, "_apm_managed", False)][0]
    assert managed.level == logging.DEBUG
    assert root.level == logging.INFO  # root unchanged
    assert logging.getLogger("app.outline").level == logging.DEBUG
