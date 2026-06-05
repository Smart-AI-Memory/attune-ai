#!/usr/bin/env python3
"""Generate the site favicon (``favicon.ico`` + ``favicon.svg``).

Re-runnable: ``python build_favicon.py``. A brand-blue rounded square
with a white lowercase "r" — matches brand.css ``--primary`` (#004ac6).
Referenced from every page's ``<head>``.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - build-time dependency
    sys.stderr.write("Pillow is required: pip install Pillow\n")
    raise SystemExit(1) from None

HERE = Path(__file__).resolve().parent
PRIMARY = (0, 74, 198)  # --primary #004ac6
WHITE = (255, 255, 255)

_FONT_CANDIDATES = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _render(px: int) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = round(px * 0.22)
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=radius, fill=PRIMARY)
    font = _font(round(px * 0.74))
    # center the glyph
    box = d.textbbox((0, 0), "r", font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((px - w) / 2 - box[0], (px - h) / 2 - box[1]), "r", font=font, fill=WHITE)
    return img


def main() -> int:
    # Multi-size ICO for crisp rendering at common sizes.
    sizes = [16, 32, 48, 64]
    imgs = [_render(s) for s in sizes]
    ico = HERE / "favicon.ico"
    imgs[1].save(ico, format="ICO", sizes=[(s, s) for s in sizes])

    # SVG for modern browsers (vector, sharp at any size).
    svg = HERE / "favicon.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#004ac6"/>'
        '<text x="16" y="23" font-family="Helvetica,Arial,sans-serif" '
        'font-size="22" font-weight="700" fill="#ffffff" '
        'text-anchor="middle">r</text></svg>\n',
        encoding="utf-8",
    )
    print(f"wrote {ico} ({ico.stat().st_size:,} bytes) + {svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
