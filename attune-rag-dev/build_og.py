#!/usr/bin/env python3
"""Generate the social-share Open Graph image (``og.png``, 1200x630).

Re-runnable: ``python build_og.py``. Referenced by ``index.html`` and
``discipline/index.html`` as ``https://attune-rag.dev/og.png`` and cached via
``vercel.json``. Uses the brand dark theme (matches ``brand.css``).
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
OUT = HERE / "og.png"

W, H = 1200, 630
BG = (11, 28, 48)  # --bg dark (#0b1c30)
INK = (232, 236, 245)  # --ink dark (#e8ecf5)
ACCENT = (102, 153, 255)  # lightened --primary for contrast on dark
MUTED = (150, 160, 180)

_FONT_CANDIDATES = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
_FONT_CANDIDATES_REG = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _font(size: int, candidates: tuple[str, ...]) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def main() -> int:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # accent rule on the left edge
    d.rectangle([0, 0, 12, H], fill=ACCENT)

    pad = 90
    # eyebrow
    eyebrow = _font(30, _FONT_CANDIDATES)
    d.text((pad, 110), "LLM-AGNOSTIC RAG PIPELINE", font=eyebrow, fill=ACCENT)

    # wordmark
    title = _font(150, _FONT_CANDIDATES)
    d.text((pad, 175), "attune-rag", font=title, fill=INK)

    # tagline (two lines, hand-wrapped)
    tag = _font(46, _FONT_CANDIDATES_REG)
    d.text((pad, 365), "Measured faithfulness, gated by CI.", font=tag, fill=MUTED)
    d.text((pad, 420), "Works with Claude, Gemini, or any LLM.", font=tag, fill=MUTED)

    # footer url
    foot = _font(34, _FONT_CANDIDATES)
    d.text((pad, 525), "attune-rag.dev", font=foot, fill=ACCENT)

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, {W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
