#!/usr/bin/env python3
"""Enforce deprecation-marker version contracts.

Modules and call sites tagged ``REMOVE IN vX.Y.Z`` must be removed
before the codebase ships version ``X``. This script reads the
current version from ``pyproject.toml`` and scans the source tree
for markers whose major version is *less than or equal to* the
current major. Any match means a previously-scheduled deletion has
silently rotted past its deadline.

Background: lesson in ``.claude/CLAUDE.md`` ("Past-due deprecations
are deletion targets, not implementation targets") and the
attune-ai 6.x cleanup that surfaced six ``REMOVE IN v4.0.0`` markers
three majors overdue.

Usage:
    python scripts/check_deprecation_markers.py
    python scripts/check_deprecation_markers.py --root src/

Exit codes:
    0 — every marker is scheduled for a future major
    1 — at least one marker is past due (offenders printed to stderr)
    2 — pyproject.toml could not be read or the marker syntax is bad
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Match REMOVE IN v<MAJOR>.<MINOR>.<PATCH> on any line. Permissive about
# preceding text so we catch markers in module docstrings, sphinx
# ``.. deprecated::`` blocks, and inline ``# REMOVE IN`` comments.
MARKER_RE = re.compile(r"REMOVE IN v(\d+)\.(\d+)\.(\d+)")

# Files to ignore even if they contain marker-like text (this script
# itself defines the pattern; the lessons file documents the rule).
SELF_REFERENTIAL: frozenset[str] = frozenset(
    {
        "scripts/check_deprecation_markers.py",
        ".claude/CLAUDE.md",
        ".claude/lessons.md",
        "tests/unit/test_deprecation_markers.py",
    }
)


def _read_current_major(pyproject: Path) -> int:
    """Return the current major version from pyproject.toml."""
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read {pyproject}: {exc}") from exc

    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"could not parse version from {pyproject}")
    return int(match.group(1))


def _iter_files(root: Path) -> list[Path]:
    """Yield .py and .md files under ``root`` that we should scan."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".md"}:
            continue
        if any(part in {"__pycache__", ".venv", "node_modules"} for part in path.parts):
            continue
        rel = path.relative_to(root.parent if root.name == "src" else root)
        if str(rel).replace("\\", "/") in SELF_REFERENTIAL:
            continue
        files.append(path)
    return files


def scan(root: Path, current_major: int) -> list[tuple[Path, int, str, tuple[int, int, int]]]:
    """Return list of past-due markers as (path, lineno, line, (M, m, p))."""
    offenders: list[tuple[Path, int, str, tuple[int, int, int]]] = []
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = MARKER_RE.search(line)
            if not match:
                continue
            major, minor, patch = (int(g) for g in match.groups())
            if major <= current_major:
                offenders.append((path, lineno, line.strip(), (major, minor, patch)))
    return offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("src"),
        help="directory to scan (default: src/)",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="path to pyproject.toml (default: pyproject.toml)",
    )
    args = parser.parse_args(argv)

    current_major = _read_current_major(args.pyproject)
    offenders = scan(args.root, current_major)

    if not offenders:
        print(
            f"[deprecation-markers] OK — no past-due markers under "
            f"{args.root} (current major: v{current_major}.x.x)"
        )
        return 0

    print(
        f"[deprecation-markers] FAIL — {len(offenders)} marker(s) past "
        f"due (current major: v{current_major}.x.x):",
        file=sys.stderr,
    )
    for path, lineno, line, version in offenders:
        major, minor, patch = version
        print(
            f"  {path}:{lineno}  REMOVE IN v{major}.{minor}.{patch}  " f"({line[:80]})",
            file=sys.stderr,
        )
    print(
        "\nFix: either delete the deprecated code and its marker, or "
        "bump the marker to a future major (and update the migration "
        "plan that gates the deletion).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
