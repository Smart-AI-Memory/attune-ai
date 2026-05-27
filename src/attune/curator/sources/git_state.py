"""Git state source reader — three discrete repo-health signals.

* diverged-from-main: HEAD's commit-date is >3 days behind
  ``origin/main`` (signals stale branch);
* uncommitted-files: ``git status --porcelain`` reports >10 entries;
* secrets-shaped untracked: untracked files whose names match common
  credential file patterns (per the CLAUDE.md "filename smell test"
  lesson).

Subprocess calls use argv-list form with ``timeout=5s``. A locked or
hung git repo collapses to a no-signal empty summary rather than a
traceback.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "git-state"
_DETAIL_CHAR_LIMIT = 500
_GIT_TIMEOUT_S = 5.0
_STALE_DAYS_THRESHOLD = 3
_UNCOMMITTED_THRESHOLD = 10

# Filename patterns that suggest credential content. Conservative —
# false positives are cheap (one curator item the user dismisses),
# false negatives leave real keys exposed.
_SECRETS_FILENAME_PATTERNS = (
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*token.*\.txt$", re.IGNORECASE),
    re.compile(r".*api[_-]?key.*", re.IGNORECASE),
)


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Probe the project_root git repo for stale / dirty / leaky state."""
    del since  # noqa: F841 — git signals are instantaneous, no since-window

    started = time.perf_counter()

    if shutil.which("git") is None:
        return _empty_summary(started)
    if not (project_root / ".git").exists():
        return _empty_summary(started)

    items: list[SourceItem] = []
    items.extend(_diverged_signal(project_root))
    items.extend(_uncommitted_signal(project_root))
    items.extend(_secrets_signal(project_root))

    state_hash = _hash_items(items)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _diverged_signal(project_root: Path) -> list[SourceItem]:
    """Emit an item if HEAD's date is >3 days behind origin/main."""
    head_dt = _commit_date(project_root, "HEAD")
    main_dt = _commit_date(project_root, "origin/main")
    if head_dt is None or main_dt is None:
        return []
    delta = main_dt - head_dt
    if delta.days < _STALE_DAYS_THRESHOLD:
        return []
    detail = (
        f"HEAD is {delta.days} days behind origin/main "
        f"(HEAD: {head_dt.date().isoformat()}, "
        f"main: {main_dt.date().isoformat()})."
    )
    return [
        SourceItem(
            item_id=f"git:diverged:{delta.days}d",
            title=f"Branch is {delta.days} days behind origin/main",
            detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
            link="",
            metadata={
                "signal": "diverged",
                "days_behind": str(delta.days),
            },
        )
    ]


def _uncommitted_signal(project_root: Path) -> list[SourceItem]:
    """Emit an item if `git status --porcelain` has >10 entries."""
    result = _run_git(project_root, ["status", "--porcelain"])
    if result is None:
        return []
    lines = [line for line in result.splitlines() if line.strip()]
    if len(lines) <= _UNCOMMITTED_THRESHOLD:
        return []
    sample = lines[:5]
    detail = f"{len(lines)} uncommitted entries in working tree. Sample: {'; '.join(sample)}"
    return [
        SourceItem(
            item_id=f"git:uncommitted:{len(lines)}",
            title=f"{len(lines)} uncommitted files in working tree",
            detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
            link="",
            metadata={
                "signal": "uncommitted",
                "count": str(len(lines)),
            },
        )
    ]


def _secrets_signal(project_root: Path) -> list[SourceItem]:
    """Emit one item per untracked file whose name looks credential-shaped."""
    result = _run_git(
        project_root,
        ["ls-files", "--others", "--exclude-standard"],
    )
    if result is None:
        return []
    suspicious: list[str] = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        name = Path(line).name
        if any(p.match(name) for p in _SECRETS_FILENAME_PATTERNS):
            suspicious.append(line)
        if len(suspicious) >= 10:
            break
    if not suspicious:
        return []
    out: list[SourceItem] = []
    for path in suspicious:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        out.append(
            SourceItem(
                item_id=f"git:secret-shape:{digest}",
                title=f"Untracked credential-shaped file: {path}",
                detail=_truncate(
                    f"Untracked file '{path}' matches a credential-shape "
                    "filename pattern. Move out of the working tree or "
                    "add to .gitignore + verify no real secrets inside.",
                    _DETAIL_CHAR_LIMIT,
                ),
                link="",
                metadata={
                    "signal": "secret_shape",
                    "path": path,
                },
            )
        )
    return out


def _commit_date(project_root: Path, ref: str) -> datetime | None:
    out = _run_git(
        project_root,
        ["log", "-1", "--format=%cI", ref],
    )
    if out is None:
        return None
    line = out.strip().splitlines()[0] if out.strip() else ""
    if not line:
        return None
    try:
        dt = datetime.fromisoformat(line)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _run_git(project_root: Path, argv: list[str]) -> str | None:
    """Argv-list git invocation with timeout. Returns stdout or None on failure."""
    try:
        proc = subprocess.run(
            ["git", *argv],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("git_state: %s timed out / failed: %s", argv, exc)
        return None
    if proc.returncode != 0:
        logger.debug(
            "git_state: %s exited %d: %s",
            argv,
            proc.returncode,
            proc.stderr.strip()[:200],
        )
        return None
    return proc.stdout


def _hash_items(items: list[SourceItem]) -> str:
    rows = sorted(item.item_id for item in items)
    return hashlib.sha256("|".join(rows).encode("utf-8")).hexdigest()[:16]


def _empty_summary(started: float) -> SourceSummary:
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=hashlib.sha256(b"").hexdigest()[:16],
        items=[],
        fetch_ms=int((time.perf_counter() - started) * 1000),
    )


def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"
