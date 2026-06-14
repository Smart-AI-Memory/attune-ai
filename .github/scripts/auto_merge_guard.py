#!/usr/bin/env python3
"""Path-class guard for the ``auto-merge-safe`` workflow.

Decides whether a PR's changed-file set is wholly within the
pre-authorized auto-merge class (test/docs only). The whole point
is to be **tight and fail-closed**: anything that isn't provably
test/docs keeps the PR out of the class, and an empty file set is
treated as unsafe.

In-class paths (every changed path must match one):

- under ``tests/``
- under ``docs/``
- under ``.help/``
- a root-level markdown file (``*.md`` with no ``/`` in the path)

Everything else — ``src/``, ``.github/``, ``pyproject.toml``,
lockfiles, ``mkdocs.yml`` — is out-of-class by construction. The
guard itself lives under ``.github/`` so a PR that edits it is
out-of-class and can never self-auto-merge.

CLI:
    python .github/scripts/auto_merge_guard.py PATH [PATH ...]
    printf '%s\\n' tests/a.py docs/b.md | python .github/scripts/auto_merge_guard.py

Exit 0 = safe (all in-class); exit 1 = unsafe (prints offenders).
"""

from __future__ import annotations

import sys

# Directory prefixes that are in-class. Trailing slash is required
# so ``.help`` cannot be matched by a sibling like ``.helpers/``.
SAFE_DIR_PREFIXES: tuple[str, ...] = ("tests/", "docs/", ".help/")


def is_in_class(path: str) -> bool:
    """Return True if a single changed path is within the class.

    Args:
        path: A repo-relative POSIX path (no leading slash), as
            returned by the GitHub PR "files" API.

    Returns:
        True iff the path is under an in-class directory or is a
        root-level ``*.md`` file. Empty paths and paths containing
        a ``..`` segment are rejected (fail-closed / traversal
        defense).
    """
    if not path:
        return False
    if ".." in path.split("/"):
        return False
    if path.startswith(SAFE_DIR_PREFIXES):
        return True
    # Root-level markdown: README.md, CHANGELOG.md, etc.
    return "/" not in path and path.endswith(".md")


def is_safe_change(paths: list[str]) -> tuple[bool, list[str]]:
    """Classify a full changed-file set.

    Args:
        paths: All changed paths for the PR. The caller should
            include each rename's previous path as well, so a move
            out of ``src/`` is caught.

    Returns:
        ``(safe, offending)`` where ``safe`` is True only if every
        path is in-class and the set is non-empty. ``offending``
        lists the out-of-class paths.
    """
    # Fail-closed: an empty set is not a provable test/docs PR.
    if not paths:
        return False, []
    offending = [p for p in paths if not is_in_class(p)]
    return (not offending), offending


def main(argv: list[str]) -> int:
    """CLI entry point. Paths from argv or, if none, stdin lines."""
    if len(argv) > 1:
        paths = [p.strip() for p in argv[1:] if p.strip()]
    else:
        paths = [line.strip() for line in sys.stdin if line.strip()]

    safe, offending = is_safe_change(paths)
    if safe:
        print(f"SAFE: all {len(paths)} path(s) within the auto-merge class")
        return 0

    if not paths:
        print("UNSAFE: empty changed-file set (fail-closed)")
    else:
        print("UNSAFE: out-of-class path(s):")
        for p in offending:
            print(f"  {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
