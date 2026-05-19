"""Generate ``thumbnail.png`` for each template under ``backend/templates/``.

A 640×360 (16:9) brand-tinted card showing:

* Background gradient from ``primary`` → ``primary-2``
* An accent colour stripe + brand-name block
* The template ``display_name`` in the heading font slot, plus the
  one-line description
* Three colour swatches (primary / accent / neutral)
* A footer with the template ``name`` slug

We deliberately *do not* render the actual ``master.pptx`` first slide
via LibreOffice headless: that would add a heavyweight runtime dependency
that the rest of the project does not need. A Pillow-rendered branded
card is enough for the template picker — the master.pptx itself is
already a faithful preview once the user opens it.

Run from the repository root::

    python backend/templates/_make_thumbnails.py

Idempotent: re-running overwrites ``thumbnail.png`` in each template dir.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 640, 360

_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")


# Mirror of _DISPLAY in app/api/templates.py — kept tiny + duplicated so this
# script has no dependency on the FastAPI app import graph.
_DISPLAY: dict[str, tuple[str, str]] = {
    "executive-dark": (
        "Executive Dark",
        "Premium dark · executive briefings, launches",
    ),
    "minimal-light": (
        "Minimal Light",
        "Minimal light · pitches, consulting",
    ),
    "tech-blue": (
        "Tech Blue",
        "Tech blue · engineering, SaaS launches",
    ),
}


def _rgb(value: str | None, fallback: str) -> tuple[int, int, int]:
    m = _HEX_RE.search(value or "")
    hex6 = (m.group(1) if m else fallback).upper()
    return (int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16))


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Best-effort TTF lookup; fall back to Pillow's default bitmap font."""
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    candidates_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates_bold if bold else candidates_regular:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _vertical_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        r = round(top[0] * (1 - t) + bottom[0] * t)
        g = round(top[1] * (1 - t) + bottom[1] * t)
        b = round(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def _draw_thumbnail(name: str, theme: dict) -> Image.Image:
    primary = _rgb(theme.get("primary"), "1F6FEB")
    primary2 = _rgb(theme.get("primary-2"), "0D1117")
    accent = _rgb(theme.get("accent"), "39D0D8")
    text_col = _rgb(theme.get("text"), "FFFFFF")
    neutral = _rgb(theme.get("neutral"), "F4F1EA")
    text_mute = _rgb(theme.get("text-mute"), "A3A6AD")

    img = _vertical_gradient(primary, primary2)
    draw = ImageDraw.Draw(img)

    # Accent stripe down the left edge.
    draw.rectangle([(0, 0), (10, HEIGHT)], fill=accent)

    # Heading + sub.
    display_name, description = _DISPLAY.get(
        name,
        (name.replace("-", " ").title(), "Custom template"),
    )
    draw.text((40, 64), display_name, fill=text_col, font=_font(38, bold=True))
    draw.text((40, 124), description, fill=text_mute, font=_font(16))

    # Swatch row.
    swatch_y = HEIGHT - 90
    swatch_size = 38
    gap = 14
    swatches = [primary, accent, neutral]
    for i, col in enumerate(swatches):
        x = 40 + i * (swatch_size + gap)
        draw.rectangle(
            [(x, swatch_y), (x + swatch_size, swatch_y + swatch_size)],
            fill=col,
            outline=text_mute,
            width=1,
        )

    # Footer: 16:9 · <name>
    footer = f"16:9 · {name}"
    draw.text((40, HEIGHT - 32), footer, fill=text_mute, font=_font(14))

    # Mock "AI" badge top-right (tiny ribbon).
    badge_w, badge_h = 56, 24
    bx, by = WIDTH - badge_w - 24, 24
    draw.rectangle([(bx, by), (bx + badge_w, by + badge_h)], fill=accent)
    draw.text((bx + 14, by + 4), "AI", fill=primary2, font=_font(14, bold=True))

    return img


def build_all() -> list[Path]:
    written: list[Path] = []
    for child in sorted(HERE.iterdir()):
        if not child.is_dir():
            continue
        mapping_file = child / "layout-mapping.yaml"
        if not mapping_file.is_file():
            continue
        data = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
        theme = data.get("theme") or {}
        img = _draw_thumbnail(child.name, theme)
        out = child / "thumbnail.png"
        img.save(out, format="PNG", optimize=True)
        written.append(out)
        print(f"  wrote {out.relative_to(HERE.parent.parent)}", file=sys.stderr)
    return written


if __name__ == "__main__":
    paths = build_all()
    print(f"generated {len(paths)} thumbnail(s)")
