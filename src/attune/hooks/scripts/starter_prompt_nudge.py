#!/usr/bin/env python
"""SessionStart hook: surface next_session_starter.md handoffs when present.

Eliminates the cross-session handoff friction documented in the
``feedback_cross_account_handoff`` memory: previously, the starter
prompt had to be pasted manually at the start of each new session.

Surfaces the most-specific handoff first (session-start-integrity
R9, OQ1 ruled RETIRE 2026-08-18):

1. **Tracked branch handoff** ``docs/handoffs/<branch-slug>.md`` for
   the CURRENT branch (slug = branch with ``/`` → ``-``), else the
   newest tracked handoff in ``docs/handoffs/``. Tracked artifacts
   are provenance-safe by construction — they live in the repo they
   describe.
2. **Project-local** ``<repo-root>/.attune/next_session_starter.md``
   — the repo-scoped queue. ``<repo-root>`` is the git toplevel
   discovered by walking up from the cwd.
3. **Global** ``~/.attune/next_session_starter.md`` — LEGACY,
   surfaced only when nothing above exists, and explicitly labeled:
   the un-namespaced global file produced the 2026-08-18 cross-repo
   false-verification and is being retired.

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

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STARTER_PATH = Path.home() / ".attune" / "next_session_starter.md"

#: Relative location of a per-repo handoff, under the git toplevel.
PROJECT_STARTER_RELPATH = Path(".attune") / "next_session_starter.md"

#: Tracked per-branch handoffs (cross-provider-session-handoff spec).
HANDOFFS_RELPATH = Path("docs") / "handoffs"

#: Non-handoff files living in docs/handoffs/ to skip.
HANDOFF_SKIP_NAMES = frozenset({"readme.md", "template.md"})

#: Timeout for the single ``git branch --show-current`` call (seconds).
#: The registered SessionStart timeout is 3s (``.claude/settings.json``);
#: this sits BELOW it so interpreter start-up, file stats, and the print
#: still fit before the harness SIGKILLs the hook. At the boundary (git
#: timeout == registered timeout) a wedged git — index.lock contention, a
#: hung filesystem — consumes the whole budget and the handoff banner is
#: lost. ``git branch --show-current`` is a local, near-instant read, so
#: 2s never truncates a healthy call; it only bounds a stuck one.
GIT_TIMEOUT = 2


def _repo_root(start: Path | None = None) -> Path | None:
    """Return the git toplevel walking up from ``start`` (default cwd)."""
    if start is None:
        start = Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _current_branch(repo_root: Path) -> str | None:
    """Current branch name, or None on detached HEAD / any git error."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
            cwd=str(repo_root),
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _size_or_zero(path: Path) -> int:
    """File size, or 0 when missing/unreadable (cross-review F4 —
    a handoff vanishing mid-scan must degrade, not crash the hook)."""
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _mtime_or_zero(path: Path) -> float:
    """File mtime, or 0.0 when missing/unreadable."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def find_handoff(repo_root: Path) -> tuple[Path, str] | None:
    """Best tracked handoff: (path, scope label), or None.

    The current branch's ``docs/handoffs/<branch-slug>.md`` wins;
    otherwise the newest handoff by mtime. Empty files and
    README/template are skipped.
    """
    handoffs_dir = repo_root / HANDOFFS_RELPATH
    if not handoffs_dir.is_dir():
        return None
    branch = _current_branch(repo_root)
    if branch:
        candidate = handoffs_dir / (branch.replace("/", "-") + ".md")
        if _size_or_zero(candidate) > 0:
            return candidate, "handoff:branch"
    candidates = [
        p
        for p in handoffs_dir.glob("*.md")
        if p.name.lower() not in HANDOFF_SKIP_NAMES and _size_or_zero(p) > 0
    ]
    if not candidates:
        return None
    newest = max(candidates, key=lambda p: _mtime_or_zero(p))
    return newest, "handoff:newest"


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


def _emit_notice(path: Path, scope: str, suffix: str = "") -> bool:
    """Print the starter-prompt notice for ``path`` if it has content.

    ``scope`` is a short label ("handoff:branch" / "project" /
    "global:LEGACY") shown in the notice; ``suffix`` appends extra
    guidance. Returns True if a notice was printed, False on any
    no-op (missing / empty / vanished file).
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
        "read this for cross-session handoff context." + suffix
    )
    return True


def main() -> int:
    """Surface the best handoff surface, most-specific first (R9)."""
    repo_root = _repo_root()
    emitted = False

    if repo_root is not None:
        handoff = find_handoff(repo_root)
        if handoff is not None:
            emitted = _emit_notice(handoff[0], handoff[1]) or emitted

    project_path = _find_project_starter()
    if project_path is not None:
        emitted = _emit_notice(project_path, "project") or emitted

    # LEGACY fallback only: the un-namespaced global file is retiring
    # (session-start-integrity R9) — never advertise it unlabeled, and
    # only when no repo-scoped surface exists.
    if not emitted and (project_path is None or STARTER_PATH.resolve() != project_path.resolve()):
        _emit_notice(
            STARTER_PATH,
            "global:LEGACY",
            " (retiring surface — migrate content to docs/handoffs/ or" " the project starter)",
        )
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
