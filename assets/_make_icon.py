"""Generate assets/app.ico (multi-resolution) for the AI PPT Maker installer.

Design: rounded square with orange→magenta gradient, white slide-deck glyph,
small "AI" sparkle badge top-right. Run once on Linux/macOS/Windows with Pillow:

    python assets/_make_icon.py

Outputs:  assets/app.ico  (sizes 16, 32, 48, 64, 128, 256)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


SIZES = [16, 32, 48, 64, 128, 256]
OUT = Path(__file__).resolve().parent / "app.ico"

# Brand palette: warm gradient that reads well at 16px and 256px.
GRAD_TOP = (255, 138, 0)      # vivid orange
GRAD_BOT = (220, 38, 99)      # magenta-pink
SLIDE_FILL = (255, 255, 255)
SLIDE_LINE = (60, 60, 70)
SPARK = (255, 215, 0)


def _gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), GRAD_TOP)
    px = img.load()
    for y in range(size):
        t = y / (size - 1) if size > 1 else 0
        r = int(GRAD_TOP[0] + (GRAD_BOT[0] - GRAD_TOP[0]) * t)
        g = int(GRAD_TOP[1] + (GRAD_BOT[1] - GRAD_TOP[1]) * t)
        b = int(GRAD_TOP[2] + (GRAD_BOT[2] - GRAD_TOP[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return img


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def _slide_glyph(size: int) -> Image.Image:
    """White 'slide deck' glyph: two stacked rounded rectangles + text lines."""
    g = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    # Back slide (offset)
    pad = int(size * 0.18)
    w = size - 2 * pad
    h = int(w * 0.62)
    x0 = pad + int(size * 0.05)
    y0 = pad + int(size * 0.10)
    r = max(2, int(size * 0.04))
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=r,
                        fill=(255, 255, 255, 110))
    # Front slide
    fx0 = pad - int(size * 0.02)
    fy0 = pad + int(size * 0.18)
    d.rounded_rectangle((fx0, fy0, fx0 + w, fy0 + h), radius=r,
                        fill=SLIDE_FILL)
    # Text lines on front slide
    line_h = max(2, int(size * 0.045))
    line_gap = max(2, int(size * 0.06))
    line_x = fx0 + int(size * 0.10)
    line_y = fy0 + int(size * 0.14)
    line_w_full = w - int(size * 0.20)
    widths = [1.0, 0.75, 0.55]
    for i, frac in enumerate(widths):
        y = line_y + i * (line_h + line_gap)
        d.rounded_rectangle(
            (line_x, y, line_x + int(line_w_full * frac), y + line_h),
            radius=max(1, line_h // 2), fill=SLIDE_LINE,
        )
    return g


def _ai_spark(size: int) -> Image.Image:
    """Small 'AI' sparkle badge in top-right corner."""
    g = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    badge_r = int(size * 0.18)
    cx = size - badge_r - int(size * 0.06)
    cy = badge_r + int(size * 0.06)
    # 4-point spark (diamond + perpendicular spikes)
    arms = badge_r
    points_outer = [
        (cx, cy - arms),
        (cx + int(arms * 0.30), cy - int(arms * 0.30)),
        (cx + arms, cy),
        (cx + int(arms * 0.30), cy + int(arms * 0.30)),
        (cx, cy + arms),
        (cx - int(arms * 0.30), cy + int(arms * 0.30)),
        (cx - arms, cy),
        (cx - int(arms * 0.30), cy - int(arms * 0.30)),
    ]
    d.polygon(points_outer, fill=SPARK)
    if size >= 64:
        # Inner highlight for depth
        inner = [
            (cx, cy - int(arms * 0.55)),
            (cx + int(arms * 0.55), cy),
            (cx, cy + int(arms * 0.55)),
            (cx - int(arms * 0.55), cy),
        ]
        d.polygon(inner, fill=(255, 245, 180))
    return g


def _compose(size: int) -> Image.Image:
    base = _gradient(size).convert("RGBA")
    mask = _rounded_mask(size, radius=max(2, int(size * 0.18)))
    rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded.paste(base, (0, 0), mask=mask)

    # Subtle inner shadow at the bottom for depth (only at larger sizes)
    if size >= 64:
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle(
            (0, int(size * 0.55), size - 1, size - 1),
            radius=max(2, int(size * 0.18)),
            fill=(0, 0, 0, 40),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=size * 0.04))
        rounded = Image.alpha_composite(rounded, shadow)
        # Re-clip to rounded shape
        clipped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        clipped.paste(rounded, (0, 0), mask=mask)
        rounded = clipped

    rounded = Image.alpha_composite(rounded, _slide_glyph(size))
    if size >= 32:
        rounded = Image.alpha_composite(rounded, _ai_spark(size))
    return rounded


def main() -> None:
    layers = [_compose(s) for s in SIZES]
    # Pillow's ICO writer takes the largest image and the desired sizes list.
    largest = max(layers, key=lambda im: im.size[0])
    largest.save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=[im for im in layers if im is not largest],
    )
    print(f"[OK] wrote {OUT} ({OUT.stat().st_size} bytes, sizes={SIZES})")


if __name__ == "__main__":
    main()
