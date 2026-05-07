import pytest

from app.outline.repair import JsonRepairError, repair


def test_plain_json():
    assert repair('{"a": 1}') == {"a": 1}


def test_fenced_json():
    raw = "```json\n{\"a\": 1}\n```"
    assert repair(raw) == {"a": 1}


def test_prose_prefix():
    raw = 'Sure! Here is your JSON:\n{"title":"x","sections":[]}\nthanks.'
    assert repair(raw) == {"title": "x", "sections": []}


def test_trailing_comma():
    raw = '{"a": 1, "b": [1,2,3,],}'
    assert repair(raw) == {"a": 1, "b": [1, 2, 3]}


def test_nested_braces_in_string():
    raw = '{"text": "use {placeholders}"}'
    assert repair(raw) == {"text": "use {placeholders}"}


def test_unparseable():
    with pytest.raises(JsonRepairError):
        repair("not json at all")


def test_top_level_array_rejected():
    with pytest.raises(JsonRepairError):
        repair("[1,2,3]")
