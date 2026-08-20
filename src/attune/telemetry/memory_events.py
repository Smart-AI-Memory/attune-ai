"""Canonical, src-importable writer for short-term memory events.

The memory hooks record what they *inject* via their own copy of this
logic in ``plugin/hooks/_memory_telemetry.py`` (not importable from
``src/``). This module is the src-side sibling: it lets code inside the
package — notably the deletion seam in
``attune.memory.session_stash`` — append ``memory_feedback`` events to
the same ``~/.attune/telemetry/memory_events.jsonl``, in the same
format and under the same local-only consent gate.

One event = one JSON line: ``v`` / ``ts`` / ``event`` / optional
``session_id`` / event-specific fields.

Consent model matches the hook copy: LOCAL recording is default-on
(like ``usage.jsonl``); nothing here ever leaves the machine.
``DO_NOT_TRACK`` or ``ATTUNE_MEMORY_TELEMETRY=0`` disables the local
log. Never raises — callers are best-effort and their telemetry must
be too.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FALSEY = {"", "0", "false", "no", "off"}

#: Rotate when the live file exceeds this (events are ~200 bytes; a
#: years-of-headroom backstop, not an expected path). Mirrors the hook.
_MAX_BYTES = 5 * 1024 * 1024


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
    """Append one memory event line. Best-effort, never raises.

    Args:
        event: Event name (e.g. ``memory_feedback``).
        session_id: Claude Code session id, when the caller has one.
        **fields: Event-specific data (e.g. ``verdict``, ``source``,
            ``count``, ``cwd``).
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
        for reserved in ("v", "ts", "event", "session_id"):
            fields.pop(reserved, None)
        record.update(fields)

        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _rotate_if_huge(path)
        with path.open("a", encoding="utf-8") as fh:
            json.dump(record, fh, separators=(",", ":"), default=str)
            fh.write("\n")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry about best-effort paths must never
        # break the caller (or the session) it observes.
        pass
