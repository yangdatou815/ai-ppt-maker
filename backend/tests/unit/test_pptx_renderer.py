"""Unit tests for app.render.pptx_renderer."""
from __future__ import annotations

import io

import pptx

from app.render.pptx_renderer import _Theme, render_outline
from app.schemas.outline import Bullet, OutlineDoc, Section
from app.schemas.template import TemplateInfo


def _doc(n_sections: int = 2) -> OutlineDoc:
    return OutlineDoc(
        title="Demo Title",
        subtitle="Demo Subtitle",
        language="zh",
        sections=[
            Section(
                heading=f"Section {i + 1}",
                bullets=[Bullet(text=f"point {i + 1}", emphasis=(i == 0))],
                speaker_notes=f"note {i + 1}" if i == 0 else None,
            )
            for i in range(n_sections)
        ],
        cover_meta={"company": "ACME", "author": "YDT"},
    )


def _template(theme: dict[str, str] | None = None) -> TemplateInfo:
    return TemplateInfo(
        name="t",
        display_name="t",
        description="",
        tags=[],
        theme=theme
        or {
            "primary": "#0B1F3A",
            "primary-2": "#050B14",
            "accent": "#C9A24E",
            "text": "#F4F1EA",
            "text-mute": "#A3A6AD",
            "neutral": "#F4F1EA",
        },
        fonts={"heading": "Calibri", "body": "Calibri"},
        has_master=False,
        thumbnail_url=None,
    )


def test_render_outline_returns_valid_pptx_bytes():
    data = render_outline(_doc(3), _template())
    assert data[:4] == b"PK\x03\x04"
    prs = pptx.Presentation(io.BytesIO(data))
    # cover + N sections + closing
    assert len(prs.slides) == 3 + 2


def test_render_outline_speaker_notes_go_to_notes_pane():
    data = render_outline(_doc(1), _template())
    prs = pptx.Presentation(io.BytesIO(data))
    # First content slide is index 1 (after cover)
    notes = prs.slides[1].notes_slide.notes_text_frame.text
    assert "note 1" in notes


def test_theme_falls_back_when_hex_garbage():
    bad = _template(theme={"primary": "not-a-color", "accent": "ZZZZZZ"})
    # Must not raise — defaults kick in.
    theme = _Theme.from_template(bad)
    assert theme.primary is not None
    assert theme.accent is not None


def test_render_outline_handles_empty_sections():
    doc = OutlineDoc(title="Empty", language="en", sections=[])
    data = render_outline(doc, _template())
    prs = pptx.Presentation(io.BytesIO(data))
    # cover + closing only
    assert len(prs.slides) == 2
