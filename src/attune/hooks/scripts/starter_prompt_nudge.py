#!/usr/bin/env python
"""SessionStart hook: surface next_session_starter.md handoffs when present.

Eliminates the cross-session handoff friction documented in the
``feedback_cross_account_handoff`` memory: previously, the starter
prompt had to be pasted manually at the start of each new session.

Surfaces the most-specific handoff first (session-start-integrity
R9, OQ1 ruled RETIRE 2026-08-18):

1. **Branch handoff** ``docs/handoffs/<branch-slug>.md`` for the CURRENT
   branch (slug = branch with ``/`` → ``-``), else a handoff selected by
   filesystem mtime, with filename breaking ties. Targets outside the repo
   are rejected. Untracked drafts and unavailable tracking checks carry
   explicit labels; Git tracking does not verify the handoff's content.
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
import time
from datetime import datetime, timezone
from pathlib import Path

STARTER_PATH = Path.home() / ".attune" / "next_session_starter.md"

#: Relative location of a per-repo handoff, under the git toplevel.
PROJECT_STARTER_RELPATH = Path(".attune") / "next_session_starter.md"

#: Tracked per-branch handoffs (cross-provider-session-handoff spec).
HANDOFFS_RELPATH = Path("docs") / "handoffs"

#: Non-handoff files living in docs/handoffs/ to skip.
HANDOFF_SKIP_NAMES = frozenset({"readme.md", "template.md"})

#: Shared timeout for branch lookup and tracked-file inventory (seconds).
#: The registered SessionStart timeout is 3s (``.claude/settings.json``);
#: this sits BELOW it so interpreter start-up, file stats, and the print
#: still fit before the harness SIGKILLs the hook. At the boundary (git
#: timeout == registered timeout) a wedged git — index.lock contention, a
#: hung filesystem — consumes the whole budget and the handoff banner is
#: lost. The inventory receives only the time left after branch lookup.
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


def _validated_local_file(path: Path, repo_root: Path) -> bool:
    """Whether a nonempty file resolves inside this repository."""
    try:
        path.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return _size_or_zero(path) > 0


def _tracked_files(repo_root: Path, deadline: float) -> set[str] | None:
    """Read indexed paths within the remaining shared Git budget."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=remaining,
            cwd=str(repo_root),
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return set(result.stdout.split("\0"))


def find_handoff(repo_root: Path) -> tuple[Path, str] | None:
    """Best contained handoff: (path, truthful scope label), or None.

    The current branch's ``docs/handoffs/<branch-slug>.md`` wins;
    otherwise use filesystem mtime, then filename for equal timestamps.
    Empty files, outside targets and README/template are skipped. Untracked
    content is labeled draft; unavailable index checks are unverified.
    """
    handoffs_dir = repo_root / HANDOFFS_RELPATH
    if not handoffs_dir.is_dir():
        return None
    candidates = [
        p
        for p in handoffs_dir.glob("*.md")
        if p.name.lower() not in HANDOFF_SKIP_NAMES and _validated_local_file(p, repo_root)
    ]
    if not candidates:
        return None
    deadline = time.monotonic() + GIT_TIMEOUT
    branch = _current_branch(repo_root)
    branch_name = branch.replace("/", "-") + ".md" if branch else None
    candidate = next((p for p in candidates if p.name == branch_name), None)
    scope = "handoff:branch"
    if candidate is None:
        candidate = max(candidates, key=lambda p: (_mtime_or_zero(p), p.name))
        scope = "handoff:fallback"
    tracked = _tracked_files(repo_root, deadline)
    try:
        resolved_name = candidate.resolve(strict=True).relative_to(repo_root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return None
    if tracked is None:
        scope += ":unverified"
    elif candidate.relative_to(repo_root).as_posix() not in tracked or resolved_name not in tracked:
        scope += ":draft"
    return candidate, scope


def _find_project_starter(start: Path | None = None) -> Path | None:
    """Return ``<git-toplevel>/.attune/next_session_starter.md`` or None.

    Walks up from ``start`` (default: cwd) looking for a ``.git``
    entry (dir for a normal checkout, file for a worktree/submodule).
    Returns the nonempty project starter when it resolves inside the repo;
    None otherwise. ``start`` is a
    parameter so tests can pin the search root.
    """
    if start is None:
        start = Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            candidate = parent / PROJECT_STARTER_RELPATH
            return candidate if _validated_local_file(candidate, parent) else None
    return None


def select_starters(
    repo_root: Path | None, project_path: Path | None, global_path: Path
) -> list[tuple[Path, str]]:
    """Select handoff and project context, with a legacy-only global fallback.

    Both starter hooks use this selection so reconciliation covers exactly
    the artifacts advertised by the nudge. Empty or vanished files are skipped.
    """
    selected: list[tuple[Path, str]] = []
    if repo_root is not None:
        handoff = find_handoff(repo_root)
        if handoff is not None:
            selected.append(handoff)
    if (
        repo_root is not None
        and project_path is not None
        and _validated_local_file(project_path, repo_root)
    ):
        selected.append((project_path, "project"))
    if not selected and _size_or_zero(global_path) > 0:
        selected.append((global_path, "global:LEGACY"))
    return selected


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
    for path, scope in select_starters(_repo_root(), _find_project_starter(), STARTER_PATH):
        suffix = ""
        if scope == "global:LEGACY":
            suffix = (
                " (retiring surface — migrate content to docs/handoffs/ or the project starter)"
            )
        elif scope.startswith("handoff:"):
            if ":fallback" in scope:
                suffix += " (fallback by filesystem mtime; not verified authoring order)"
            if scope.endswith(":draft"):
                suffix += " (untracked handoff draft)"
            elif scope.endswith(":unverified"):
                suffix += " (Git tracking unverified)"
        _emit_notice(path, scope, suffix)
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
