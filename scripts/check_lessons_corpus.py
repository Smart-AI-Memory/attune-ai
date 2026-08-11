#!/usr/bin/env python3
"""Guard: every lesson entry in the corpus starts with ``- **``.

``attune.lessons.split_lessons`` anchors entry parsing on RAW lines
beginning ``- **``. An entry whose title is bolded but NOT bulleted
(``**Title**: body``) does not start a new document — the splitter
glues its text onto the END of the preceding lesson's body. The text
is still findable as a substring, but it can never be the top hit for
its own topic and its title never surfaces in recall.

Found 2026-08-11: 28 such orphans had accumulated in a 998-entry
corpus. ``attune.docs_outbox`` gates artifacts entering through the
sweep (PR #2055), but the corpus is also hand-edited, which that gate
never sees. This is the corpus-side half.

Usage::

    python scripts/check_lessons_corpus.py            # check, exit 1 on orphans
    python scripts/check_lessons_corpus.py --fix      # prefix orphans with "- "

Licensed under the Apache License, Version 2.0
Copyright 2026 Smart AI Memory, LLC
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / ".claude" / "lessons.md"
HEADING = "## Lessons Learned"


def find_orphans(lines: list[str]) -> list[int]:
    """Return 0-based indices of bolded-but-unbulleted entry starts.

    An orphan is a column-0 ``**`` line that OPENS a block (preceded by
    a blank line or the section heading). A ``**`` line mid-paragraph is
    continuation prose, not an entry start, and is left alone.
    """
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(HEADING))
    except StopIteration:
        return []
    orphans = []
    for i in range(start + 1, len(lines)):
        if not lines[i].startswith("**"):
            continue
        if lines[i - 1].strip() == "":
            orphans.append(i)
    return orphans


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="prefix orphans with '- '")
    parser.add_argument("--path", type=Path, default=CORPUS)
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"corpus not found: {args.path}", file=sys.stderr)
        return 1

    text = args.path.read_text(encoding="utf-8")
    lines = text.splitlines()
    orphans = find_orphans(lines)
    if not orphans:
        return 0

    if not args.fix:
        # --path may point outside the repo (tests), where relative_to raises.
        try:
            shown = args.path.relative_to(REPO_ROOT)
        except ValueError:
            shown = args.path
        print(
            f"{len(orphans)} lesson entr{'y is' if len(orphans) == 1 else 'ies are'} bolded but "
            f"not bulleted in {shown}.\n"
            "The splitter anchors on '- **', so each is swallowed into the "
            "PRECEDING lesson instead of being its own entry.\n"
            "Fix: python scripts/check_lessons_corpus.py --fix\n",
            file=sys.stderr,
        )
        for i in orphans:
            print(f"  line {i + 1}: {lines[i][:70]}", file=sys.stderr)
        return 1

    for i in orphans:
        lines[i] = "- " + lines[i]
    # splitlines() drops the trailing newline; the corpus must keep it.
    args.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"fixed {len(orphans)} orphan entr{'y' if len(orphans) == 1 else 'ies'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
