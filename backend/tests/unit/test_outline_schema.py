"""Tests for OutlineDoc schema robustness against common LLM quirks."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.outline import OutlineDoc


def _minimal(**overrides):
    base = {
        "title": "Demo",
        "language": "zh",
        "sections": [{"heading": "S1", "bullets": []}],
    }
    base.update(overrides)
    return base


def test_cover_meta_drops_null_values():
    """LLMs often emit ``"date": null`` for unknown fields; we should drop
    them rather than fail (regression for the 'Fallback (LLM 不可用)' badge
    appearing on otherwise-good LLM output)."""
    doc = OutlineDoc.model_validate(
        _minimal(cover_meta={"author": "Alice", "date": None, "company": None}),
    )
    assert doc.cover_meta == {"author": "Alice"}


def test_cover_meta_coerces_non_string_values_to_string():
    doc = OutlineDoc.model_validate(_minimal(cover_meta={"year": 2026}))
    assert doc.cover_meta == {"year": "2026"}


def test_cover_meta_empty_when_all_null():
    doc = OutlineDoc.model_validate(_minimal(cover_meta={"a": None, "b": None}))
    assert doc.cover_meta == {}


def test_cover_meta_default_is_empty_dict():
    doc = OutlineDoc.model_validate(_minimal())
    assert doc.cover_meta == {}


def test_cover_meta_rejects_non_dict():
    with pytest.raises(ValidationError):
        OutlineDoc.model_validate(_minimal(cover_meta="not a dict"))
