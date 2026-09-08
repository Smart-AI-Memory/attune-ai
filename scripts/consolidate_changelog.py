#!/usr/bin/env python3
"""Merge duplicate ``###`` headers inside one CHANGELOG release section.

Why this exists: PRs append their own ``### Added`` / ``### Changed`` /
``### Fixed`` block under ``[Unreleased]`` rather than inserting under
the existing one, so by release time the section carries the same
header several times over. Cutting 16.3.0 (2026-09-08) found seven
headers -- two Added, two Changed, three Fixed -- and they were merged
by hand, which is both error-prone and unrecorded.

The merge is order-preserving and idempotent: entries keep their order
within each category, categories come out in Keep-a-Changelog order
(Added, Changed, Deprecated, Removed, Fixed, Security) with any
unrecognized header appended in first-seen order, and running it twice
changes nothing.

Usage::

    python scripts/consolidate_changelog.py 16.3.0
    python scripts/consolidate_changelog.py 16.3.0 --check
    python scripts/consolidate_changelog.py Unreleased --path CHANGELOG.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

#: Keep a Changelog's canonical order. Anything else keeps first-seen
#: position after these, rather than being dropped or alphabetized.
CANONICAL_ORDER = (
    "### Added",
    "### Changed",
    "### Deprecated",
    "### Removed",
    "### Fixed",
    "### Security",
)


def _section_bounds(lines: list[str], version: str) -> tuple[int, int]:
    """Return the ``[start, end)`` line span of one release section.

    ``version`` is matched as the ``## [<version>]`` heading. Raises
    ``LookupError`` when the section is absent -- a silent no-op here
    would read as "nothing to consolidate" on a typo'd version.
    """
    heading = f"## [{version}]"
    start = None
    for i, line in enumerate(lines):
        if line.startswith(heading):
            start = i
            break
    if start is None:
        raise LookupError(f"no {heading} section in the changelog")
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ["):
            return start, i
    return start, len(lines)


def consolidate(text: str, version: str) -> str:
    """Return ``text`` with the version's duplicate ``###`` headers merged."""
    lines = text.splitlines(keepends=True)
    start, end = _section_bounds(lines, version)

    intro: list[str] = []
    blocks: dict[str, list[str]] = {}
    seen: list[str] = []
    current: str | None = None
    for line in lines[start:end]:
        if line.startswith("### "):
            current = line.strip()
            if current not in blocks:
                blocks[current] = []
                seen.append(current)
            continue
        (intro if current is None else blocks[current]).append(line)

    ordered = [h for h in CANONICAL_ORDER if h in blocks]
    ordered += [h for h in seen if h not in CANONICAL_ORDER]

    rebuilt = "".join(intro).rstrip("\n") + "\n\n"
    for header in ordered:
        body = "".join(blocks[header]).strip("\n")
        rebuilt += f"{header}\n\n{body}\n\n" if body else f"{header}\n\n"
    if end == len(lines):
        # Last section in the file: a trailing blank line here would
        # make the transform mutate an ALREADY-CLEAN changelog, so
        # --check could never report success on it.
        rebuilt = rebuilt.rstrip("\n") + "\n"
    return "".join(lines[:start]) + rebuilt + "".join(lines[end:])


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. ``--check`` reports without writing."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help='release section to merge, e.g. "16.3.0" or "Unreleased"')
    parser.add_argument("--path", type=Path, default=Path("CHANGELOG.md"), help="changelog file")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether consolidation is needed; write nothing (exit 1 when it is)",
    )
    args = parser.parse_args(argv)

    original = args.path.read_text(encoding="utf-8")
    try:
        merged = consolidate(original, args.version)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if merged == original:
        print(f"[{args.version}] headers already consolidated")
        return 0
    if args.check:
        print(f"[{args.version}] has duplicate ### headers -- run without --check to merge")
        return 1
    args.path.write_text(merged, encoding="utf-8")
    print(f"[{args.version}] headers consolidated")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
