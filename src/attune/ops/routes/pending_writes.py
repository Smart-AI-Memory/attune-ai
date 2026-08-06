"""Pending-writes API — GET /api/pending-writes.

See `docs/specs/dashboard-pending-writes-journal/` for the full
design. Phase 1: read the journal, enrich each entry with computed
fields (current disk sha, is_committed via git status, dashboard
liveness, age), return JSON.

Consumers filter per their needs (UI chip uses uncommitted_count;
session-start hook uses is_committed=false; auditors use
matches_journal=false). The API returns everything enriched, not
pre-filtered — see D3 in decisions.md.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from attune.ops import pending_writes as journal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["pending-writes"])


def _load_journal_entries(journal_path: Path) -> list[dict[str, Any]]:
    """Read JSONL journal; return list of entry dicts.

    Best-effort: corrupt lines are skipped with a WARNING log. Missing
    journal file returns empty list (no error — a fresh install has
    no journal).
    """
    if not journal_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        text = journal_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("pending_writes: cannot read journal at %s: %s", journal_path, exc)
        return []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.warning(
                "pending_writes: corrupt journal line %d in %s: %s",
                lineno,
                journal_path,
                exc,
            )
    return entries


def _is_dashboard_running(pid: int) -> bool:
    """Best-effort: does this PID belong to a running process?

    Uses ``os.kill(pid, 0)`` which doesn't send a real signal but
    raises ``ProcessLookupError`` if the pid is dead and
    ``PermissionError`` if the pid is alive but owned by another
    user (we can't signal it).
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still counts as alive.
        return True
    except OSError:
        return False
    return True


def _collect_dirty_paths(project_root: Path) -> set[str] | None:
    """One ``git status --porcelain -uall`` for the whole root.

    Replaces the previous per-entry ``git status -- <file>`` calls
    (N subprocess spawns per request) with a single call per distinct
    project root. ``-uall`` lists individual untracked files instead
    of collapsing directories, so membership checks stay per-file.

    Returns:
        Set of dirty paths (posix-style, relative to the root), or
        None if the status couldn't be determined (no git repo, git
        missing, timeout).
    """
    if not project_root.is_dir():
        return None
    try:
        result = subprocess.run(  # noqa: S603 — fixed argv, validated root
            ["git", "-C", str(project_root), "status", "--porcelain=v1", "-uall"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("pending_writes: git status failed for %s: %s", project_root, exc)
        return None
    if result.returncode != 0:
        return None
    dirty: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:]
        # Renames render as "old -> new"; both sides are dirty.
        parts = path_part.split(" -> ") if " -> " in path_part else [path_part]
        for part in parts:
            cleaned = part.strip()
            # git C-quotes paths with special characters.
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            if cleaned:
                dirty.add(cleaned)
    return dirty


def _is_file_committed(
    file_path: Path,
    project_root: Path,
    dirty_paths: set[str] | None,
) -> bool | None:
    """Is this file clean per the batched ``git status`` result?

    Returns:
        True  — file is under the root and not in the dirty set
        False — file appears as modified / untracked / staged
        None  — couldn't determine (git failed, file outside root)
    """
    if dirty_paths is None:
        return None
    try:
        rel = file_path.relative_to(project_root)
    except ValueError:
        # file is not under project_root — out of scope for this check
        return None
    return rel.as_posix() not in dirty_paths


def _system_tmp_prefix() -> str:
    """Platform-native system tempdir as a path prefix.

    Covers Windows ``%TEMP%`` / ``%TMP%`` (typically
    ``C:\\Users\\<user>\\AppData\\Local\\Temp``), Linux ``$TMPDIR``,
    and macOS default. ``startswith()`` matches against the same
    separator form the journal writer recorded
    (``os.sep`` from ``str(Path(...))``).
    """
    return tempfile.gettempdir().rstrip(os.sep) + os.sep


_TMP_PATH_PREFIXES: tuple[str, ...] = (  # nosec B108 — filter prefixes, not file I/O
    _system_tmp_prefix(),
    "/tmp/",  # nosec B108
    "/private/tmp/",  # nosec B108
    "/var/folders/",
    "/private/var/folders/",
    "/var/tmp/",  # nosec B108
    "/private/var/tmp/",  # nosec B108
)
"""Known transient-directory prefixes — pytest tmp_path, OS scratch
dirs. Entries whose project_root lives under any of these are
test-fixture pollution, even when the dir still exists at read
time (macOS pytest keeps the last few tmp dirs alive).

First entry is the platform tempdir (covers Windows
``AppData\\Local\\Temp``). The static POSIX entries cover macOS's
``/private/var/folders/...pytest-of-...`` cases that survive even
when ``TMPDIR`` is overridden by tests or CI."""


def _is_real_entry(entry: dict[str, Any]) -> bool:
    """Drop test-fixture / stale entries at read time.

    Two-part heuristic. A journal entry is "real" if its
    ``project_root``:
      - is present
      - is NOT under a known transient-directory prefix
        (``/tmp``, ``/var/folders/...pytest``, etc.)
      - points at an existing directory on disk

    Tmp-path prefixes catch pytest fixtures even while they're
    still alive (macOS pytest holds the last few runs). Existence
    check catches stale entries from projects the user has since
    deleted or moved.

    This is a READ-side filter only — the journal itself stays as
    the append-only source of truth (see D1 in decisions.md).
    Auditors who need the raw stream can read
    ``~/.attune/ops/pending_writes.jsonl`` directly.
    """
    pr = entry.get("project_root", "")
    if not isinstance(pr, str) or not pr:
        return False
    # Tmp-path prefix exclusion runs BEFORE the existence check
    # because macOS keeps pytest tmp_path dirs alive across runs.
    if any(pr.startswith(prefix) for prefix in _TMP_PATH_PREFIXES):
        return False
    try:
        return Path(pr).is_dir()
    except (OSError, ValueError):
        return False


def _enrich(
    entry: dict[str, Any],
    now: datetime,
    dirty_by_root: dict[str, set[str] | None],
) -> dict[str, Any]:
    """Add computed fields to a journal entry.

    Adds:
        dashboard_still_running: bool
        current_disk_sha256: str | None
        matches_journal: bool
        is_committed: bool | None
        age_seconds: int | None
    """
    enriched = dict(entry)

    pid = entry.get("dashboard_pid")
    enriched["dashboard_still_running"] = (
        _is_dashboard_running(int(pid)) if isinstance(pid, int) else False
    )

    project_root_str = entry.get("project_root", "")
    file_path_rel = entry.get("file_path", "")
    project_root = Path(project_root_str) if project_root_str else None
    abs_file_path: Path | None = None
    if project_root is not None and file_path_rel:
        abs_file_path = project_root / file_path_rel

    enriched["current_disk_sha256"] = (
        journal.compute_file_sha256(abs_file_path) if abs_file_path else None
    )
    enriched["matches_journal"] = (
        enriched["current_disk_sha256"] == entry.get("after_sha256")
        if enriched["current_disk_sha256"] is not None
        else False
    )
    enriched["is_committed"] = (
        _is_file_committed(abs_file_path, project_root, dirty_by_root.get(project_root_str))
        if abs_file_path and project_root
        else None
    )

    ts_raw = entry.get("ts", "")
    try:
        entry_ts = datetime.fromisoformat(ts_raw)
        enriched["age_seconds"] = int((now - entry_ts).total_seconds())
    except (ValueError, TypeError):
        enriched["age_seconds"] = None

    return enriched


def _summarize(enriched_entries: list[dict[str, Any]]) -> dict[str, int]:
    """Compute summary counts across the enriched entries."""
    total = len(enriched_entries)
    uncommitted = sum(1 for e in enriched_entries if e.get("is_committed") is False)
    stale = sum(1 for e in enriched_entries if not e.get("dashboard_still_running"))
    drifted = sum(1 for e in enriched_entries if not e.get("matches_journal"))
    return {
        "total_entries": total,
        "uncommitted_count": uncommitted,
        "stale_dashboard_count": stale,
        "drifted_count": drifted,
    }


@router.get("/pending-writes")
def list_pending_writes(request: Request) -> dict[str, Any]:
    """Return all journal entries enriched with computed status fields.

    See `docs/specs/dashboard-pending-writes-journal/design.md` for
    the response shape.

    Consumers should filter per their needs (e.g. dashboard UI chip
    uses ``uncommitted_count``; a session-start hook filters
    entries where ``is_committed`` is False).

    Deliberately a sync (``def``) handler: FastAPI runs it in the
    threadpool, keeping the git subprocess + sha256 file reads off
    the event loop.
    """
    # Allow tests + dev to override the journal path via app.state.
    journal_path: Path = getattr(
        request.app.state, "pending_writes_journal_path", journal.JOURNAL_PATH
    )
    now = datetime.now(timezone.utc)
    raw_entries = _load_journal_entries(journal_path)
    # Filter test-fixture / stale entries before enrichment — see
    # ``_is_real_entry`` for the heuristic. Skips expensive sha256 +
    # git-status computation for entries we'd just drop anyway.
    real_entries = [e for e in raw_entries if _is_real_entry(e)]
    # One `git status` per distinct project root (not per entry).
    dirty_by_root: dict[str, set[str] | None] = {}
    for entry in real_entries:
        root = entry.get("project_root", "")
        if isinstance(root, str) and root and root not in dirty_by_root:
            dirty_by_root[root] = _collect_dirty_paths(Path(root))
    enriched = [_enrich(entry, now, dirty_by_root) for entry in real_entries]
    return {
        "pending": enriched,
        "summary": _summarize(enriched),
    }
