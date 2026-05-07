"""Programmatic PPTX renderer (M2-2).

Renders an :class:`OutlineDoc` to a python-pptx :class:`Presentation` using the
template's theme tokens (no real ``master.pptx`` required for v0.3.0). Each
section becomes one of:

- ``cover``: title + subtitle + accent rule
- ``content-bullets``: numbered heading + bullet column with emphasis-bold
- ``content-image`` / ``content-table``: handled with same content-bullets
  layout for now (image / table input is a later milestone)
- ``closing``: thank-you slide with the same accent treatment as cover

Design tokens come from ``backend/templates/<name>/layout-mapping.yaml``
(``theme:`` + ``fonts:``). Hex colours are parsed defensively — unknown keys
fall back to a sensible default rather than crashing the request.
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

from app.schemas.outline import OutlineDoc, Section
from app.schemas.template import TemplateInfo

log = logging.getLogger(__name__)

_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")
_DEFAULT_THEME = {
    "primary": "0B1F3A",
    "primary-2": "050B14",
    "accent": "C9A24E",
    "text": "F4F1EA",
    "text-mute": "A3A6AD",
    "neutral": "F4F1EA",
}
_DEFAULT_FONTS = {
    "heading": "Calibri",
    "body": "Calibri",
}


@dataclass(frozen=True)
class _Theme:
    primary: RGBColor
    primary_2: RGBColor
    accent: RGBColor
    text: RGBColor
    text_mute: RGBColor
    neutral: RGBColor
    heading_font: str
    body_font: str

    @classmethod
    def from_template(cls, t: TemplateInfo) -> _Theme:
        def _rgb(key: str) -> RGBColor:
            raw = t.theme.get(key) or _DEFAULT_THEME[key]
            m = _HEX_RE.search(raw)
            return RGBColor.from_string((m.group(1) if m else _DEFAULT_THEME[key]).upper())

        return cls(
            primary=_rgb("primary"),
            primary_2=_rgb("primary-2"),
            accent=_rgb("accent"),
            text=_rgb("text"),
            text_mute=_rgb("text-mute"),
            neutral=_rgb("neutral"),
            heading_font=t.fonts.get("heading", _DEFAULT_FONTS["heading"]),
            body_font=t.fonts.get("body", _DEFAULT_FONTS["body"]),
        )


# 16:9, 13.333" x 7.5"
_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)


def _set_slide_bg(slide, rgb: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb


def _add_rect(slide, left, top, width, height, rgb: RGBColor):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    return shape


def _add_text(
    slide,
    left,
    top,
    width,
    height,
    *,
    text: str,
    font: str,
    size_pt: int,
    color: RGBColor,
    bold: bool = False,
    align: PP_ALIGN | None = None,
):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run()
    run.text = text
    f = run.font
    f.name = font
    f.size = Pt(size_pt)
    f.bold = bold
    f.color.rgb = color
    return tb


def _cover_slide(prs: Presentation, theme: _Theme, doc: OutlineDoc) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _set_slide_bg(slide, theme.primary)

    # Accent rule above the title
    _add_rect(slide, Inches(1.0), Inches(2.4), Inches(0.6), Inches(0.06), theme.accent)
    _add_text(
        slide, Inches(1.0), Inches(2.55), Inches(11.3), Inches(1.6),
        text=doc.title,
        font=theme.heading_font, size_pt=54, color=theme.text, bold=True,
    )
    if doc.subtitle:
        _add_text(
            slide, Inches(1.0), Inches(4.2), Inches(11.3), Inches(0.8),
            text=doc.subtitle,
            font=theme.body_font, size_pt=22, color=theme.text_mute,
        )
    # Footer line
    parts = [
        doc.cover_meta.get("company"),
        doc.cover_meta.get("author"),
        doc.cover_meta.get("date"),
    ]
    footer = "  ·  ".join(p for p in parts if p)
    if footer:
        _add_text(
            slide, Inches(1.0), Inches(6.6), Inches(11.3), Inches(0.4),
            text=footer,
            font=theme.body_font, size_pt=12, color=theme.text_mute,
        )


def _section_slide(
    prs: Presentation, theme: _Theme, idx: int, total: int, section: Section,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, theme.neutral)

    # Section number gutter
    _add_text(
        slide, Inches(0.7), Inches(0.55), Inches(2.0), Inches(0.5),
        text=f"{idx:02d} / {total:02d}",
        font=theme.body_font, size_pt=12, color=theme.accent, bold=True,
    )
    # Heading
    _add_text(
        slide, Inches(0.7), Inches(1.05), Inches(11.9), Inches(1.0),
        text=section.heading,
        font=theme.heading_font, size_pt=34, color=theme.primary, bold=True,
    )
    # Accent rule
    _add_rect(slide, Inches(0.7), Inches(2.05), Inches(0.6), Inches(0.05), theme.accent)

    # Bullets
    if section.bullets:
        tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.45), Inches(11.5), Inches(4.5))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, b in enumerate(section.bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            p.space_after = Pt(8)
            run = p.add_run()
            run.text = "•  " + b.text
            run.font.name = theme.body_font
            run.font.size = Pt(20)
            run.font.bold = bool(b.emphasis)
            run.font.color.rgb = theme.primary if b.emphasis else theme.text_mute
            if b.note:
                p2 = tf.add_paragraph()
                p2.alignment = PP_ALIGN.LEFT
                r2 = p2.add_run()
                r2.text = "    — " + b.note
                r2.font.name = theme.body_font
                r2.font.size = Pt(14)
                r2.font.italic = True
                r2.font.color.rgb = theme.text_mute

    # Speaker notes go to the slide notes pane (PowerPoint reads it on the
    # presenter screen). Doesn't print, doesn't pollute the visible page.
    if section.speaker_notes:
        notes_tf = slide.notes_slide.notes_text_frame
        notes_tf.text = section.speaker_notes


def _closing_slide(prs: Presentation, theme: _Theme, doc: OutlineDoc) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, theme.primary)
    _add_rect(slide, Inches(1.0), Inches(2.4), Inches(0.6), Inches(0.06), theme.accent)
    label = "Thank you" if doc.language == "en" else "谢谢观看"
    _add_text(
        slide, Inches(1.0), Inches(2.55), Inches(11.3), Inches(1.4),
        text=label,
        font=theme.heading_font, size_pt=54, color=theme.text, bold=True,
    )
    _add_text(
        slide, Inches(1.0), Inches(4.0), Inches(11.3), Inches(0.8),
        text=doc.title,
        font=theme.body_font, size_pt=22, color=theme.text_mute,
    )


def render_outline(doc: OutlineDoc, template: TemplateInfo) -> bytes:
    """Build a .pptx for ``doc`` styled by ``template``; return the file bytes."""
    theme = _Theme.from_template(template)

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    _cover_slide(prs, theme, doc)
    total = len(doc.sections)
    for i, section in enumerate(doc.sections, start=1):
        _section_slide(prs, theme, i, total, section)
    _closing_slide(prs, theme, doc)

    buf = io.BytesIO()
    prs.save(buf)
    log.info(
        "render done: template=%s sections=%d total_slides=%d size_kb=%d",
        template.name, total, total + 2, len(buf.getvalue()) // 1024,
    )
    return buf.getvalue()
