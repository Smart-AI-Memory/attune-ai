#!/usr/bin/env python3
"""Fail CI when a README in-page link points at a heading that no longer exists.

Why this exists
---------------
The README's "Contents" nav links to headings by GitHub's auto-generated
anchor slug. Renaming a heading silently breaks every link that pointed at
it — the link still renders, it just goes nowhere, and nothing in the test
suite notices. That is exactly what happened to ``#privacy--telemetry``
after ``## Privacy & Telemetry`` became ``## Security, Privacy & Telemetry``.

This is a drift guard in the same spirit as ``check_badge_freshness.py``:
cheap, offline, and it fails loudly the moment a rename outruns the nav.

Slug rules (mirrors github-slugger, which is what GitHub renders with):
  1. lowercase
  2. drop every character that is not a letter, digit, underscore,
     hyphen, or whitespace
  3. whitespace -> hyphen
  4. a repeated slug gets ``-1``, ``-2``, ... appended, in document order

Headings inside fenced code blocks are NOT headings — a ``# comment`` in a
``bash`` block must never register as one.

Usage:
    python scripts/check_readme_anchors.py            # checks README.md
    python scripts/check_readme_anchors.py PATH ...   # checks the given files

Exit 0 when every in-page link resolves; exit 1 with a report otherwise.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ``](#anchor)`` — an in-page markdown link. Excludes ``](http...)``.
LINK_RE = re.compile(r"\]\(#([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Inline markdown that must not survive into the slug: `code`, **bold**,
# _em_, and [text](url) -> text.
INLINE_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
STRIP_MARKS_RE = re.compile(r"[`*_]")
# HTML tags occasionally used inside headings.
TAG_RE = re.compile(r"<[^>]+>")


def slugify(text: str) -> str:
    """Convert heading text to GitHub's anchor slug."""
    text = INLINE_LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub("", text)
    text = STRIP_MARKS_RE.sub("", text)
    text = text.strip().lower()
    # Keep letters, digits, underscore, hyphen and whitespace; drop the rest.
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s", "-", text)


def collect(path: Path) -> tuple[dict[str, int], list[tuple[str, int]]]:
    """Return (slug -> first line number, [(linked anchor, line number)])."""
    slugs: dict[str, int] = {}
    seen: dict[str, int] = {}
    links: list[tuple[str, int]] = []
    in_fence = False
    fence_marker = ""

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, ""
            continue
        if in_fence:
            continue

        heading = HEADING_RE.match(raw)
        if heading:
            base = slugify(heading.group(2))
            if not base:
                continue
            count = seen.get(base, 0)
            slug = base if count == 0 else f"{base}-{count}"
            seen[base] = count + 1
            slugs.setdefault(slug, lineno)

        for match in LINK_RE.finditer(raw):
            links.append((match.group(1), lineno))

    return slugs, links


def check(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path}: file not found"]

    slugs, links = collect(path)
    problems: list[str] = []

    for anchor, lineno in links:
        if anchor in slugs:
            continue
        suggestion = ""
        # Offer the closest heading that shares a distinctive word, so the
        # failure tells you what to write instead of just what broke.
        tokens = {t for t in anchor.split("-") if len(t) > 3}
        ranked = sorted(
            ((len(tokens & set(s.split("-"))), s) for s in slugs),
            reverse=True,
        )
        if ranked and ranked[0][0] > 0:
            suggestion = f"  (did you mean #{ranked[0][1]} ?)"
        problems.append(f"{path}:{lineno}: link #{anchor} matches no heading{suggestion}")

    return problems


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or [Path("README.md")]
    problems: list[str] = []
    for path in paths:
        problems.extend(check(path))

    if problems:
        print("Broken in-page README links:\n", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nA renamed heading changes its anchor. Update the link, or "
            "restore the heading text.",
            file=sys.stderr,
        )
        return 1

    checked = ", ".join(str(p) for p in paths)
    print(f"All in-page links resolve ({checked}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
