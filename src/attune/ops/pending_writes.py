"""Pending-writes journal — durable log of dashboard-driven disk writes.

See `docs/specs/dashboard-pending-writes-journal/` for the full
design. Phase 1: journal writer + module-level helpers.

The journal lives at ``~/.attune/ops/pending_writes.jsonl`` (one JSON
object per line, append-only). Each entry records a single mutating
endpoint call: when, by which dashboard process, to which file, with
before/after sha256s.

Failures here are best-effort: the actual write endpoint must NOT
be blocked by a journal-append failure. All write paths in this
module log a WARNING and swallow the exception.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Default journal path. Tests should patch via the
# ``journal_path`` kwarg on append_entry, not by mutating this.
JOURNAL_PATH: Path = Path.home() / ".attune" / "ops" / "pending_writes.jsonl"


@dataclass(frozen=True)
class JournalEntry:
    """One pending-writes journal entry.

    See `docs/specs/dashboard-pending-writes-journal/design.md` for
    the schema rationale.

    Fields:
        ts: ISO-8601 UTC timestamp (microsecond precision).
        session_id: CLAUDE_CODE_SESSION_ID env var, or ``dashboard-<pid>``
            fallback when no Claude Code session env is present (e.g.,
            the dashboard was started outside a session).
        dashboard_pid: OS pid of the dashboard process that made the
            write. Lets consumers check whether the originator is
            still alive.
        endpoint: Canonical FastAPI route path (e.g.,
            ``PUT /api/specs/{slug}/{phase}/status``).
        action: Human-readable action name (e.g., ``set_spec_status``).
        file_path: POSIX path of the written file, RELATIVE to
            ``project_root`` (forward slashes regardless of platform).
        project_root: Absolute path of the project root the file lives
            under. Disambiguates worktree-local vs main-checkout edits.
        before_sha256: sha256 of file content BEFORE the write
            (``None`` if the file was newly created).
        after_sha256: sha256 of file content AFTER the write
            (must be present).
    """

    ts: str
    session_id: str
    dashboard_pid: int
    endpoint: str
    action: str
    file_path: str
    project_root: str
    before_sha256: str | None
    after_sha256: str


def compute_file_sha256(path: Path) -> str | None:
    """Compute sha256 of a file's contents.

    Returns ``None`` if the file doesn't exist or can't be read.
    Failures are intentional: a missing or unreadable file at journal
    time is signal, not an error.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        logger.warning("compute_file_sha256: failed for %s: %s", path, exc)
        return None


def _resolve_session_id(dashboard_pid: int) -> str:
    """Best-effort session id for the journal entry.

    Returns ``CLAUDE_CODE_SESSION_ID`` if set, otherwise the
    ``dashboard-<pid>`` fallback.
    """
    env_session = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if env_session:
        return env_session
    return f"dashboard-{dashboard_pid}"


def make_entry(
    *,
    endpoint: str,
    action: str,
    file_path: str,
    project_root: str,
    before_sha256: str | None,
    after_sha256: str,
    session_id: str | None = None,
    dashboard_pid: int | None = None,
    ts: str | None = None,
) -> JournalEntry:
    """Construct a JournalEntry, filling in defaults from runtime context.

    Kwargs-only by design — callers should be explicit about what
    they're recording. Defaults handle the boilerplate (pid, session
    id, timestamp).
    """
    if dashboard_pid is None:
        dashboard_pid = os.getpid()
    if session_id is None:
        session_id = _resolve_session_id(dashboard_pid)
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    return JournalEntry(
        ts=ts,
        session_id=session_id,
        dashboard_pid=dashboard_pid,
        endpoint=endpoint,
        action=action,
        file_path=file_path,
        project_root=project_root,
        before_sha256=before_sha256,
        after_sha256=after_sha256,
    )


def append_entry(entry: JournalEntry, journal_path: Path | None = None) -> None:
    """Append a journal entry to the JSONL journal.

    Best-effort: failures log a WARNING and do not raise. The actual
    write endpoint that called this MUST NOT be blocked by a journal
    failure (see D5 in decisions.md).

    Atomic per write: POSIX ``O_APPEND`` semantics guarantee
    concurrent appends from multiple dashboard processes do not
    interleave for writes under the page size (entries are well under
    1KB).
    """
    path = journal_path if journal_path is not None else JOURNAL_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(entry), sort_keys=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except (OSError, TypeError, ValueError) as exc:
        # OSError/IOError: disk full, permission denied, etc.
        # TypeError/ValueError: dataclass serialization issue (shouldn't
        # happen with the frozen dataclass shape, but defense in depth).
        logger.warning(
            "pending_writes.append_entry: failed (%s); journal at %s",
            exc,
            path,
        )
