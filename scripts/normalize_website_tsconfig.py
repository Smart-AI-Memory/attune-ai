#!/usr/bin/env python3
"""Revert Next.js dev-server's tsconfig ``jsx`` flip (pre-commit).

``next dev`` rewrites ``website/tsconfig.json`` on every startup,
flipping ``"jsx": "react-jsx"`` to ``"jsx": "preserve"`` — a build
artifact that must never be committed (retro ruling 2026-08-29,
item 6a: auto-revert beats reject; the diff matched here is exactly
that one-line flip, so a real config change can never be eaten).

Pre-commit auto-fix convention: when the flip is present, rewrite
the file back and exit 1 (the fix lands unstaged; ``git add`` and
retry, same as black). Clean file exits 0.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TSCONFIG = Path(__file__).resolve().parents[1] / "website" / "tsconfig.json"

FLIP = re.compile(r'"jsx"\s*:\s*"preserve"')
CANONICAL = '"jsx": "react-jsx"'


def normalize(text: str) -> tuple[str, int]:
    """Return (normalized text, number of flips reverted)."""
    return FLIP.subn(CANONICAL, text)


def main() -> int:
    if not TSCONFIG.is_file():
        return 0
    text = TSCONFIG.read_text(encoding="utf-8")
    fixed, count = normalize(text)
    if count == 0:
        return 0
    TSCONFIG.write_text(fixed, encoding="utf-8")
    print(
        f"reverted next-dev's jsx flip in {TSCONFIG.name} "
        f"({count} occurrence{'s' if count != 1 else ''}) — re-add and retry"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
