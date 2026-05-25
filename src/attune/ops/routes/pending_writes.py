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


def _is_file_committed(file_path: Path, project_root: Path) -> bool | None:
    """Does ``git status --porcelain`` show this file as clean?

    Returns:
        True  — file exists, git treats it as committed (no dirty status)
        False — file appears as modified / untracked / staged in git status
        None  — couldn't determine (no git repo, git command failed, etc.)
    """
    if not project_root.is_dir():
        return None
    try:
        rel = file_path.relative_to(project_root)
    except ValueError:
        # file is not under project_root — out of scope for this check
        return None
    try:
        result = subprocess.run(  # noqa: S603 — args are derived from validated paths
            ["git", "-C", str(project_root), "status", "--porcelain", "--", str(rel)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("pending_writes: git status check failed for %s: %s", file_path, exc)
        return None
    if result.returncode != 0:
        # Not a git repo, or git couldn't read the file. Treat as unknown.
        return None
    # Empty output from `git status --porcelain -- <file>` means clean
    # (no dirty status). Non-empty means modified/untracked/staged/etc.
    return result.stdout.strip() == ""


def _enrich(entry: dict[str, Any], now: datetime) -> dict[str, Any]:
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
        _is_file_committed(abs_file_path, project_root) if abs_file_path and project_root else None
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
async def list_pending_writes(request: Request) -> dict[str, Any]:
    """Return all journal entries enriched with computed status fields.

    See `docs/specs/dashboard-pending-writes-journal/design.md` for
    the response shape.

    Consumers should filter per their needs (e.g. dashboard UI chip
    uses ``uncommitted_count``; a session-start hook filters
    entries where ``is_committed`` is False).
    """
    # Allow tests + dev to override the journal path via app.state.
    journal_path: Path = getattr(
        request.app.state, "pending_writes_journal_path", journal.JOURNAL_PATH
    )
    now = datetime.now(timezone.utc)
    raw_entries = _load_journal_entries(journal_path)
    enriched = [_enrich(entry, now) for entry in raw_entries]
    return {
        "pending": enriched,
        "summary": _summarize(enriched),
    }
