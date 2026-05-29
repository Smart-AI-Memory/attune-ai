"""Shared state-discovery helpers for session-continuity hooks.

Pure-Python module — no Claude Code SDK calls, no network I/O.
Used by `spec_orient.py`, `compact_warning.py`, and the
`/handoff` slash command.

Three responsibilities:

1. ``discover_specs(roots)`` — walk every ``specs/`` directory
   under ``roots`` for in-flight specs, returns most-recently
   modified first.
2. ``git_state(cwd)`` — branch + last commit + uncommitted file
   list. Tolerates missing git or non-repo paths.
3. ``session_sentinel_path(session_id)`` — the once-per-session
   file used by ``compact_warning.py`` so the warning fires
   exactly once.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# Phases checked, highest-priority first. The first phase file
# present in a spec directory determines the displayed phase
# and status.
_PHASE_FILES: tuple[tuple[str, str], ...] = (
    ("tasks", "tasks.md"),
    ("design", "design.md"),
    ("requirements", "requirements.md"),
)

_STATUS_LINE = re.compile(
    r"^\s*\*\*?Status\*\*?\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Sentinel TTL: anything older than this on a SessionStart prune
# sweep is considered orphaned from an ungraceful exit.
_SENTINEL_TTL_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class SpecInfo:
    """One in-flight spec discovered under a workspace root."""

    slug: str
    """Directory name, e.g. ``precompact-sessionstart-hooks``."""

    path: Path
    """Absolute path to the spec directory."""

    layer: str
    """Layer slug (``workspace`` for root specs, else
    ``attune-rag`` / ``attune-help`` / etc.)."""

    phase: str
    """``requirements`` | ``design`` | ``tasks``."""

    status: str
    """Verbatim status line value, lowercased
    (e.g. ``approved``, ``in-progress``, ``draft``)."""

    mtime: float
    """Most-recent mtime across spec files (seconds since epoch)."""


@dataclass(frozen=True)
class GitState:
    """Snapshot of the worktree's git state at hook fire time."""

    branch: str
    last_sha: str
    last_subject: str
    uncommitted: tuple[str, ...]


def _read_status(path: Path) -> str:
    """Return the lowercased status from a phase file, or empty."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = _STATUS_LINE.search(text)
    if not match:
        return ""
    return match.group(1).strip().lower()


def _phase_for_dir(spec_dir: Path) -> tuple[str, str, float] | None:
    """Pick the highest-priority phase file present in a spec dir.

    Returns ``(phase, status, mtime)`` where ``mtime`` is the most
    recent across all phase files (so adding a fresh file bumps
    the spec to the top of the list).

    Returns ``None`` when no phase file is readable.
    """
    chosen: tuple[str, str, float] | None = None
    latest_mtime = 0.0
    for phase, fname in _PHASE_FILES:
        fpath = spec_dir / fname
        if not fpath.is_file():
            continue
        try:
            file_mtime = fpath.stat().st_mtime
        except OSError:
            continue
        if file_mtime > latest_mtime:
            latest_mtime = file_mtime
        if chosen is None:
            status = _read_status(fpath)
            chosen = (phase, status, 0.0)
    if chosen is None:
        return None
    return chosen[0], chosen[1], latest_mtime


def _is_in_flight(phase: str, status: str) -> bool:
    """Decide whether a spec is in-flight per the requirements.

    Rules:
    - tasks.md ``Status: complete`` → done, exclude.
    - Any other phase/status with a present phase file → in-flight.
    - Empty status (malformed) → still in-flight (don't drop a
      working spec because the heading was malformed).
    """
    if phase == "tasks" and status == "complete":
        return False
    return True


def _layer_for(roots: list[Path], base: Path) -> str:
    """Resolve the layer slug for a spec's base directory.

    ``base`` is the directory that *contains* the spec subdir
    (``specs`` or ``docs/specs``) — either the workspace root or a
    layer dir.

    Workspace-root specs → ``workspace``.
    Layer specs (``<workspace>/attune-rag/...``) → ``attune-rag``.
    """
    if base in roots:
        return "workspace"
    return base.name or "workspace"


# Spec-subdir conventions probed under each root and layer dir.
# attune-gui and workspace-root specs live in ``specs/``;
# attune-rag/author/help keep theirs in ``docs/specs/``. Probing both
# lets one identical hook serve every repo (supersedes a per-repo
# config). Root-level matches are processed before layer matches so a
# root ``docs/specs`` is attributed to ``workspace`` (see dedup below).
_SPEC_SUBDIRS: tuple[str, ...] = ("specs", "docs/specs")


def discover_specs(roots: list[Path]) -> list[SpecInfo]:
    """Walk ``specs/`` directories under each root for in-flight specs.

    Args:
        roots: Workspace roots to scan. Each root is checked for a
            top-level ``specs/`` and for ``<root>/<layer>/specs/``
            directories (one nested level only — no recursive walk).

    Returns:
        ``SpecInfo`` list, most-recently modified first. Tolerates
        missing dirs and malformed status lines.
    """
    found: list[SpecInfo] = []
    seen: set[Path] = set()
    for root in roots:
        # (base, specs_dir) pairs. ``base`` is the dir that contains the
        # spec subdir and decides the layer label. Root-level bases are
        # listed first so a ``docs/specs`` at the root is attributed to
        # ``workspace`` before the layer walk reaches the same path.
        candidate_bases: list[tuple[Path, Path]] = [(root, root / sub) for sub in _SPEC_SUBDIRS]
        try:
            for entry in sorted(root.iterdir()):
                if entry.is_dir():
                    candidate_bases.extend((entry, entry / sub) for sub in _SPEC_SUBDIRS)
        except OSError:
            continue
        for base, specs_dir in candidate_bases:
            if not specs_dir.is_dir():
                continue
            try:
                spec_dirs = sorted(p for p in specs_dir.iterdir() if p.is_dir())
            except OSError:
                continue
            for spec_dir in spec_dirs:
                resolved = spec_dir.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                phase_info = _phase_for_dir(spec_dir)
                if phase_info is None:
                    continue
                phase, status, mtime = phase_info
                if not _is_in_flight(phase, status):
                    continue
                found.append(
                    SpecInfo(
                        slug=spec_dir.name,
                        path=spec_dir,
                        layer=_layer_for(roots, base),
                        phase=phase,
                        status=status,
                        mtime=mtime,
                    )
                )
    found.sort(key=lambda s: s.mtime, reverse=True)
    return found


def _run_git(cwd: Path, *args: str) -> str:
    """Run a git command and return stdout, or empty on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def git_state(cwd: Path) -> GitState:
    """Return branch, last commit, and uncommitted files for ``cwd``.

    Empty fields when ``cwd`` isn't a git repo or git is missing.
    """
    branch = _run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if not branch:
        return GitState(branch="", last_sha="", last_subject="", uncommitted=())
    log_output = _run_git(cwd, "log", "-1", "--format=%h%x09%s")
    last_sha = ""
    last_subject = ""
    if log_output:
        parts = log_output.strip().split("\t", 1)
        last_sha = parts[0]
        if len(parts) > 1:
            last_subject = parts[1]
    porcelain = _run_git(cwd, "status", "--porcelain")
    uncommitted: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        # Porcelain format: ``XY <path>`` (status flags + space + path).
        path = line[3:].strip()
        if path:
            uncommitted.append(path)
    return GitState(
        branch=branch,
        last_sha=last_sha,
        last_subject=last_subject,
        uncommitted=tuple(uncommitted),
    )


def _sentinel_dir() -> Path:
    """Resolve the directory used for once-per-session sentinels.

    Honors ``ATTUNE_AI_SENTINEL_DIR`` for tests; otherwise uses
    ``~/.attune``. The Claude Code session-state directory is
    not documented as an env var as of 2026-05, so the
    ``~/.attune`` fallback is the primary path.
    """
    override = os.environ.get("ATTUNE_AI_SENTINEL_DIR")
    if override:
        return Path(override)
    return Path.home() / ".attune"


def session_sentinel_path(session_id: str | None) -> Path:
    """Path to the once-per-session compact-warning sentinel.

    Uses a sanitized session id so the path stays inside the
    sentinel dir even with weird inputs.
    """
    base = _sentinel_dir()
    safe = "unknown"
    if session_id:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:64] or "unknown"
    return base / f".compact-warned-{safe}"


def prune_stale_sentinels(now: float | None = None) -> int:
    """Delete sentinel files older than the TTL.

    Returns the number of files removed. Safe to call when the
    sentinel dir doesn't exist.
    """
    sentinel_dir = _sentinel_dir()
    if not sentinel_dir.is_dir():
        return 0
    cutoff = (now if now is not None else time.time()) - _SENTINEL_TTL_SECONDS
    removed = 0
    try:
        entries = list(sentinel_dir.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if not entry.name.startswith(".compact-warned-"):
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def workspace_roots(cwd: Path | None = None) -> list[Path]:
    """Best-effort guess at workspace roots to scan for specs.

    Order:
    1. ``ATTUNE_AI_WORKSPACE_ROOTS`` env var
       (``os.pathsep``-separated: ``:`` on POSIX, ``;`` on Windows).
    2. The given ``cwd`` (or the process cwd).
    3. ``~/attune`` if it exists and isn't already in the list.
    """
    override = os.environ.get("ATTUNE_AI_WORKSPACE_ROOTS")
    if override:
        return [Path(p) for p in override.split(os.pathsep) if p]
    base = (cwd or Path.cwd()).resolve()
    roots: list[Path] = [base]
    home_workspace = Path.home() / "attune"
    if home_workspace.is_dir() and home_workspace.resolve() not in {r.resolve() for r in roots}:
        roots.append(home_workspace)
    return roots
