#!/usr/bin/env python3
"""Path-class guard for the ``auto-merge-safe`` workflow.

Decides whether a PR's changed-file set is wholly within a
pre-authorized auto-merge class. The whole point is to be **tight
and fail-closed**: anything that isn't provably in-class keeps the
PR out, and an empty file set is treated as unsafe.

Two modes (``--mode``):

``tests-docs`` (default) — every changed path must match one of:

- under ``tests/``
- under ``docs/``
- under ``.help/``
- a root-level markdown file (``*.md`` with no ``/`` in the path)

Everything else — ``src/``, ``.github/``, ``pyproject.toml``,
lockfiles, ``mkdocs.yml`` — is out-of-class by construction.

``when-green`` (Class 2, opt-in ``auto-merge-when-green`` label,
archive spec D8) — every path is in-class EXCEPT ``.github/``:
merge automation and CI config can never self-merge, even labeled.
Green-ness is enforced by GitHub native auto-merge (all required
checks), not by this guard.

In both modes the guard itself lives under ``.github/`` so a PR
that edits it is out-of-class and can never self-auto-merge.

CLI:
    python .github/scripts/auto_merge_guard.py [--mode MODE] PATH [PATH ...]
    printf '%s\\n' tests/a.py | python .github/scripts/auto_merge_guard.py

Exit 0 = safe (all in-class); exit 1 = unsafe (prints offenders);
exit 2 = usage error (unknown mode).
"""

from __future__ import annotations

import sys

# Directory prefixes that are in-class. Trailing slash is required
# so ``.help`` cannot be matched by a sibling like ``.helpers/``.
SAFE_DIR_PREFIXES: tuple[str, ...] = ("tests/", "docs/", ".help/")

# Prefixes BLOCKED in when-green mode: CI and merge automation can
# never self-merge, even with the opt-in label applied.
WHEN_GREEN_BLOCKED_PREFIXES: tuple[str, ...] = (".github/",)

MODES: tuple[str, ...] = ("tests-docs", "when-green")


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


def is_when_green_safe(path: str) -> bool:
    """Return True if a path is within the when-green class.

    Args:
        path: A repo-relative POSIX path (no leading slash), as
            returned by the GitHub PR "files" API.

    Returns:
        True iff the path is NOT under a blocked prefix
        (``.github/``). Empty paths and paths containing a ``..``
        segment are rejected (fail-closed / traversal defense).
    """
    if not path:
        return False
    if ".." in path.split("/"):
        return False
    return not path.startswith(WHEN_GREEN_BLOCKED_PREFIXES)


def is_safe_change(paths: list[str], mode: str = "tests-docs") -> tuple[bool, list[str]]:
    """Classify a full changed-file set.

    Args:
        paths: All changed paths for the PR. The caller should
            include each rename's previous path as well, so a move
            out of ``src/`` (or ``.github/``) is caught.
        mode: ``tests-docs`` (default, tight class) or
            ``when-green`` (opt-in class, ``.github/`` carve-out).

    Returns:
        ``(safe, offending)`` where ``safe`` is True only if every
        path is in-class and the set is non-empty. ``offending``
        lists the out-of-class paths.
    """
    predicate = is_when_green_safe if mode == "when-green" else is_in_class
    # Fail-closed: an empty set is not a provable in-class PR.
    if not paths:
        return False, []
    offending = [p for p in paths if not predicate(p)]
    return (not offending), offending


def main(argv: list[str]) -> int:
    """CLI entry point. Paths from argv or, if none, stdin lines."""
    args = argv[1:]
    mode = "tests-docs"
    if args and args[0] == "--mode":
        if len(args) < 2 or args[1] not in MODES:
            print(f"usage: auto_merge_guard.py [--mode {{{'|'.join(MODES)}}}] [PATH ...]")
            return 2
        mode = args[1]
        args = args[2:]

    if args:
        paths = [p.strip() for p in args if p.strip()]
    else:
        paths = [line.strip() for line in sys.stdin if line.strip()]

    safe, offending = is_safe_change(paths, mode=mode)
    if safe:
        print(f"SAFE: all {len(paths)} path(s) within the auto-merge class ({mode})")
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
