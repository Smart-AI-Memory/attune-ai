#!/usr/bin/env python
"""SessionStart hook: surface next_session_starter.md handoffs when present.

Eliminates the cross-session handoff friction documented in the
``feedback_cross_account_handoff`` memory: previously, the starter
prompt had to be pasted manually at the start of each new session.

Two locations are surfaced, most-specific first:

1. **Project-local** ``<repo-root>/.attune/next_session_starter.md`` —
   the handoff for THIS repo. Lets a session that hands off to a
   *different* repo (e.g. attune-ai → attune-gui) leave the starter
   where the next session in that repo will actually find it, instead
   of clobbering the single global file. ``<repo-root>`` is the git
   toplevel discovered by walking up from the cwd.
2. **Global** ``~/.attune/next_session_starter.md`` — the
   cross-cutting / cwd-agnostic handoff (back-compat with the original
   single-file behavior).

The file content itself is NOT printed inline — keeps the
SessionStart noise floor low. Users / the agent open it
explicitly when they want the handoff context.

Output is informational only. Exit code is always 0 so the
session starts normally regardless of file state.

Lives under the enforcement framework at
``docs/specs/enforcement-vs-documentation/``. This is a small,
mechanical surfacing of a recurring handoff pattern. Not a
hard-blocking enforcement (no exit 2), so it doesn't count
against the soft cap of 10 active enforcements.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

STARTER_PATH = Path.home() / ".attune" / "next_session_starter.md"

#: Relative location of a per-repo handoff, under the git toplevel.
PROJECT_STARTER_RELPATH = Path(".attune") / "next_session_starter.md"


def _find_project_starter(start: Path | None = None) -> Path | None:
    """Return ``<git-toplevel>/.attune/next_session_starter.md`` or None.

    Walks up from ``start`` (default: cwd) looking for a ``.git``
    entry (dir for a normal checkout, file for a worktree/submodule).
    Returns the project-local starter path if that file exists; None
    if no repo root is found or the file is absent. ``start`` is a
    parameter so tests can pin the search root.
    """
    if start is None:
        start = Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            candidate = parent / PROJECT_STARTER_RELPATH
            return candidate if candidate.is_file() else None
    return None


def _format_age(mtime_ts: float, now: float | None = None) -> str:
    """Return a short human-readable age like '2h ago', '3d ago'.

    ``now`` is the current Unix timestamp; defaults to
    ``datetime.now(timezone.utc).timestamp()``. Exposed as a
    parameter so tests can pin time and avoid Windows clock-source
    jitter between ``time.time()`` and ``datetime.now().timestamp()``
    that would otherwise push edge-of-bucket values across boundaries.
    """
    if now is None:
        now = datetime.now(timezone.utc).timestamp()
    delta = now - mtime_ts
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"


def _emit_notice(path: Path, scope: str) -> bool:
    """Print the starter-prompt notice for ``path`` if it has content.

    ``scope`` is a short label ("project" / "global") shown in the
    notice. Returns True if a notice was printed, False on any no-op
    (missing / empty / vanished file).
    """
    if not path.is_file():
        return False
    try:
        stat = path.stat()
    except OSError:
        # File disappeared between is_file() and stat(); just no-op.
        return False
    if stat.st_size == 0:
        # Empty file — nothing to surface.
        return False

    age = _format_age(stat.st_mtime)
    size_kb = stat.st_size / 1024
    print(
        f"[starter-prompt:{scope}] {path} ({size_kb:.1f} KB, modified {age}) — "
        "read this for cross-session handoff context."
    )
    return True


def main() -> int:
    """Surface project-local then global starter notices, if present."""
    project_path = _find_project_starter()
    if project_path is not None:
        _emit_notice(project_path, "project")

    # Always also surface the global handoff (it serves a different,
    # cwd-agnostic purpose) — unless it IS the project-local file we
    # already emitted (a repo rooted at ~ would alias the two).
    if project_path is None or STARTER_PATH.resolve() != project_path.resolve():
        _emit_notice(STARTER_PATH, "global")
    return 0


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: hook errors must never block session start.
        # Surface the failure to stderr; exit 0 so the session proceeds.
        print(
            f"[starter-prompt] hook error (continuing): " f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
