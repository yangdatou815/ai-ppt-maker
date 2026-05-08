"""Unit tests for app.render.pptx_renderer."""
from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pptx

from app.render.pptx_renderer import _pick_layout, _Theme, render_outline
from app.schemas.outline import (
    Bullet,
    ImageRef,
    OutlineDoc,
    Section,
    TableData,
)
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


# ---------------------------------------------------------------------------
# M2-3: layout_hint dispatch + image / table rendering
# ---------------------------------------------------------------------------


def _png_1x1() -> bytes:
    """Minimal valid 1x1 PNG. Lets us avoid pulling Pillow into test deps."""
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter byte + 1 RGB pixel
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def test_pick_layout_explicit_hint_wins():
    s = Section(heading="h", layout_hint="content-image",
                image=ImageRef(file_id="x.png"))
    assert _pick_layout(s) == "content-image"


def test_pick_layout_falls_back_when_hint_mismatches_payload():
    # hint says image but no image attached → fall through to inference (bullets)
    s = Section(heading="h", layout_hint="content-image",
                bullets=[Bullet(text="b")])
    assert _pick_layout(s) == "content-bullets"


def test_pick_layout_infers_from_payload():
    assert _pick_layout(Section(heading="h", image=ImageRef(file_id="a.png"))) == "content-image"
    assert _pick_layout(
        Section(heading="h", table=TableData(headers=["a"], rows=[["1"]]))
    ) == "content-table"
    assert _pick_layout(Section(heading="h")) == "content-bullets"


def test_render_table_section_creates_native_pptx_table():
    doc = OutlineDoc(
        title="T",
        language="en",
        sections=[
            Section(
                heading="Numbers",
                table=TableData(
                    headers=["Q", "Rev"],
                    rows=[["Q1", "10"], ["Q2", "20"], ["Q3", "30"]],
                    caption="quarterly",
                ),
            )
        ],
    )
    data = render_outline(doc, _template())
    prs = pptx.Presentation(io.BytesIO(data))
    table_slide = prs.slides[1]
    tables = [s for s in table_slide.shapes if s.has_table]
    assert len(tables) == 1
    tbl = tables[0].table
    # header row + 3 data rows
    assert len(tbl.rows) == 4
    assert len(tbl.columns) == 2
    assert tbl.cell(0, 0).text_frame.text == "Q"
    assert tbl.cell(2, 1).text_frame.text == "20"


def test_render_image_section_with_real_file_embeds_picture(tmp_path: Path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "pic.png").write_bytes(_png_1x1())

    doc = OutlineDoc(
        title="I",
        language="en",
        sections=[
            Section(
                heading="See chart",
                bullets=[Bullet(text="left side")],
                image=ImageRef(file_id="pic.png", caption="cap"),
            )
        ],
    )
    data = render_outline(doc, _template(), uploads_dir=uploads)
    prs = pptx.Presentation(io.BytesIO(data))
    pics = [s for s in prs.slides[1].shapes if s.shape_type == 13]  # MSO_SHAPE_TYPE.PICTURE
    assert len(pics) == 1


def test_render_image_section_placeholder_when_file_missing(tmp_path: Path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    doc = OutlineDoc(
        title="I",
        language="en",
        sections=[
            Section(heading="x", image=ImageRef(file_id="ghost.png")),
        ],
    )
    data = render_outline(doc, _template(), uploads_dir=uploads)
    prs = pptx.Presentation(io.BytesIO(data))
    # No PICTURE shapes — only the placeholder rect + text.
    pics = [s for s in prs.slides[1].shapes if s.shape_type == 13]
    assert pics == []
    # And the slide must still render (cover + 1 + closing).
    assert len(prs.slides) == 3


def test_render_image_section_rejects_path_traversal(tmp_path: Path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    secret = tmp_path / "secret.png"
    secret.write_bytes(_png_1x1())

    doc = OutlineDoc(
        title="I",
        language="en",
        sections=[
            Section(heading="x", image=ImageRef(file_id="../secret.png")),
        ],
    )
    data = render_outline(doc, _template(), uploads_dir=uploads)
    prs = pptx.Presentation(io.BytesIO(data))
    pics = [s for s in prs.slides[1].shapes if s.shape_type == 13]
    assert pics == []  # traversal rejected


def test_render_table_with_truncation_warning():
    rows = [[f"r{i}", str(i)] for i in range(20)]
    doc = OutlineDoc(
        title="T",
        language="en",
        sections=[
            Section(
                heading="Big",
                table=TableData(headers=["k", "v"], rows=rows),
            )
        ],
    )
    data = render_outline(doc, _template())
    prs = pptx.Presentation(io.BytesIO(data))
    tbls = [s for s in prs.slides[1].shapes if s.has_table]
    assert len(tbls) == 1
    # Header + 14 cap = 15 rows, regardless of input being 20.
    assert len(tbls[0].table.rows) == 15
