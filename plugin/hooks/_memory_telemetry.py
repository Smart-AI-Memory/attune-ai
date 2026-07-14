"""Best-effort event log for the short-term memory hooks.

The memory layer (session recall at the door, JIT rule recall at the
decision point, the Stop-hook stash) had no self-measurement: a
cost-savings analysis had to MODEL its token impact instead of reading
it. This module gives each hook a one-call way to record what it
actually injected, to ``~/.attune/telemetry/memory_events.jsonl`` — the
same local-only JSONL style as ``usage.jsonl``.

One event = one JSON line:

- ``v`` / ``ts`` — schema version, UTC ISO-8601 timestamp.
- ``event`` — ``session_recall`` | ``jit_recall`` | ``lesson_recall``
  | ``session_stash``.
- ``session_id`` — Claude Code session id (local file only; the
  opt-in usage ping reads ``usage*.jsonl`` and never this file).
- ``injected_chars`` / ``est_tokens`` — size of the context the hook
  injected (tokens estimated at 4 chars/token).
- event-specific fields (entry counts, tool name, rule ids, ...).

Fires-per-session (recall vs JIT counts) fall out of grouping lines by
``session_id`` + ``event``. JIT events carry ``tool`` + ``rules`` so a
later analysis can correlate "rule surfaced at time T" with whether the
matching failure occurred afterwards (prevented-failure estimation).

Consent model: matches the existing telemetry split — LOCAL recording
is default-on (like ``usage.jsonl``), and only the separate opt-in
usage ping ever leaves the machine (this file is not in its glob).
``DO_NOT_TRACK`` (the same signal ``usage_consent_notice.py`` honors)
or ``ATTUNE_MEMORY_TELEMETRY=0`` disables even the local log.

Never raises — the memory hooks are best-effort and their telemetry
must be too.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FALSEY = {"", "0", "false", "no", "off"}

#: Rotate when the live file exceeds this (events are ~200 bytes; this
#: is a years-of-headroom backstop, not an expected path).
_MAX_BYTES = 5 * 1024 * 1024

#: Rough chars-per-token divisor for the ``est_tokens`` convenience field.
_CHARS_PER_TOKEN = 4


def _enabled() -> bool:
    """False when local memory telemetry is switched off via env."""
    if os.environ.get("ATTUNE_MEMORY_TELEMETRY", "1").strip().lower() in _FALSEY:
        return False
    dnt = os.environ.get("DO_NOT_TRACK")
    return dnt is None or dnt.strip().lower() in _FALSEY


def _events_path() -> Path:
    """Resolve the live events file under ATTUNE_HOME (default ~/.attune)."""
    home = os.environ.get("ATTUNE_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".attune"
    return base / "telemetry" / "memory_events.jsonl"


def _rotate_if_huge(path: Path) -> None:
    """Best-effort size backstop: rotate to a dated sibling when huge."""
    try:
        if path.stat().st_size < _MAX_BYTES:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rotated = path.with_name(f"memory_events.{stamp}.jsonl")
        counter = 1
        while rotated.exists():
            rotated = path.with_name(f"memory_events.{stamp}.{counter}.jsonl")
            counter += 1
        path.replace(rotated)
    except OSError:
        pass  # rotation is a nicety; the append below still works


def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
    """Append one memory-hook event line. Best-effort, never raises.

    Args:
        event: Event name (``session_recall`` / ``jit_recall`` /
            ``lesson_recall`` / ``session_stash``).
        session_id: Claude Code session id, when the payload carried one.
        **fields: Event-specific data. An int ``injected_chars`` field
            gains a derived ``est_tokens`` sibling automatically.
    """
    try:
        if not _enabled():
            return
        record: dict[str, object] = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event": event,
        }
        if session_id:
            record["session_id"] = str(session_id)[:64]
        record.update(fields)
        chars = record.get("injected_chars")
        if isinstance(chars, int) and "est_tokens" not in record:
            record["est_tokens"] = chars // _CHARS_PER_TOKEN

        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _rotate_if_huge(path)
        # Single write() call per record: appends of one buffered line
        # are effectively atomic on POSIX and Windows, so concurrent
        # sessions never interleave partial JSONL lines.
        line = json.dumps(record, separators=(",", ":"), default=str) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry about best-effort hooks must never
        # break the hook (or the session) it observes.
        pass
