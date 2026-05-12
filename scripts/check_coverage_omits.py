#!/usr/bin/env python3
"""Enforce the coverage-exclusion-policy.

Every production-code entry in pyproject.toml's
`[tool.coverage.run] omit = [...]` block must have an inline `#`
comment stating why the file is excluded from coverage. Meta-excludes
(test discovery patterns, build artifacts, third-party paths) are
allowlisted and do not need a comment.

See docs/specs/coverage-exclusion-policy/ for the policy and the
allowed reason categories.

Usage:
    python scripts/check_coverage_omits.py

Exit codes:
    0 — all production-code entries documented (or only meta-excludes
        are undocumented)
    1 — at least one undocumented production-code entry; offenders
        printed to stderr
    2 — pyproject.toml or the omit block could not be located
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Meta-exclude patterns that do NOT require an inline `#` reason —
# they are self-explanatory test/build-artifact filters.
META_EXCLUDES: frozenset[str] = frozenset(
    {
        "*/tests/*",
        "*/test_*.py",
        "*/__pycache__/*",
        "*/site-packages/*",
    }
)

# Captures the first quoted pattern on a line, e.g. "*/foo/bar.py".
_PATTERN_RE = re.compile(r'"([^"]+)"')


def _find_omit_block(text: str) -> tuple[int, int] | None:
    """Return (start_line_idx, end_line_idx) for the omit list body.

    Indices are 0-based and reference lines *inside* the brackets
    (i.e. the `"..."` entries), exclusive of the `omit = [` and `]`
    delimiter lines themselves.

    Returns None if the block can't be located.
    """
    lines = text.splitlines()
    start: int | None = None
    in_coverage_run = False
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped == "[tool.coverage.run]":
            in_coverage_run = True
            continue
        # Any other section header ends the [tool.coverage.run] scope.
        if (
            in_coverage_run
            and stripped.startswith("[")
            and stripped.endswith("]")
            and "=" not in stripped
        ):
            in_coverage_run = False
        if in_coverage_run and stripped.startswith("omit"):
            # Tolerate `omit = [` or `omit=[`.
            if "[" in stripped:
                start = i + 1
                break
    if start is None:
        return None
    for j in range(start, len(lines)):
        if lines[j].strip().startswith("]"):
            return (start, j)
    return None


def _is_documented(line: str, pattern: str) -> bool:
    """Return True if the line carries a `#` comment after the quoted pattern."""
    # Drop everything up to and including the closing quote of the pattern.
    quoted = f'"{pattern}"'
    idx = line.find(quoted)
    if idx < 0:
        return False
    tail = line[idx + len(quoted) :]
    return "#" in tail


def find_undocumented(pyproject_text: str) -> list[tuple[int, str]]:
    """Find undocumented production-code omit entries.

    Returns a list of `(1-based-line-number, pattern)` tuples.
    Meta-excludes are filtered out.
    """
    block = _find_omit_block(pyproject_text)
    if block is None:
        raise RuntimeError(
            "Could not locate `[tool.coverage.run] omit = [...]` "
            "block in pyproject.toml. "
            "Has the layout changed? See "
            "docs/specs/coverage-exclusion-policy/."
        )
    start, end = block
    lines = pyproject_text.splitlines()
    offenders: list[tuple[int, str]] = []
    for line_idx in range(start, end):
        line = lines[line_idx]
        match = _PATTERN_RE.search(line)
        if not match:
            continue
        pattern = match.group(1)
        if pattern in META_EXCLUDES:
            continue
        if not _is_documented(line, pattern):
            offenders.append((line_idx + 1, pattern))
    return offenders


def main() -> int:
    """Check pyproject.toml's coverage omit block for documentation gaps."""
    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        print(f"error: {pyproject} not found", file=sys.stderr)
        return 2
    text = pyproject.read_text(encoding="utf-8")
    try:
        offenders = find_undocumented(text)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not offenders:
        return 0
    print(
        "Undocumented coverage-omit entries (each must have an " "inline `# reason` comment):",
        file=sys.stderr,
    )
    for lineno, pattern in offenders:
        print(f"  pyproject.toml:{lineno}: {pattern}", file=sys.stderr)
    print(
        "\nSee docs/specs/coverage-exclusion-policy/requirements.md "
        "for the reason-category taxonomy.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
