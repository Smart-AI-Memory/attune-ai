"""Role telemetry — round-table P4, RECORD-ONLY (issue #1587).

Ruled 2026-07-21 (thread ``q-roundtable-extensions-001``, chair:
Patrick; build order P3 → P2 → P4-recording): role telemetry starts
recording when the P2 gate-triage inbox launches. Record-only means
exactly that — this module appends events and computes read-side
derivations; NOTHING consumes it for behavior. Dissent hit-rate and
chair-latency dashboards come later, if the chair ever asks.

Events are appended to
``<ATTUNE_HOME|~/.attune>/ops/roundtable/role_telemetry.jsonl`` —
the same home-resolution idiom as the G1 verdict ledger, so the
suite's isolation fixture redirects writes automatically.

Chair latency is derived, never stored: the seconds between a
thread's ``digest-posted`` event and its ``chair-ruled`` event.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def telemetry_path() -> Path:
    """``<ATTUNE_HOME|~/.attune>/ops/roundtable/role_telemetry.jsonl``."""
    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    return attune_dir / "ops" / "roundtable" / "role_telemetry.jsonl"


def record(
    role: str,
    seat: str,
    thread: str,
    event: str,
    *,
    path: Path | None = None,
    **fields: object,
) -> Path:
    """Append one role event (append-only; never deletes, never blocks).

    A telemetry write failure is logged and swallowed — recording is
    an observation surface, not a dependency of the pass it observes.
    """
    dest = path or telemetry_path()
    row = {
        "role": role,
        "seat": seat,
        "thread": thread,
        "event": event,
        "at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError as exc:
        logger.warning("role-telemetry: write failed (%s); event dropped", exc)
    return dest


def record_chair_ruling(thread: str, *, path: Path | None = None, **fields: object) -> Path:
    """Record the chair's ruling touch on a thread (the latency endpoint)."""
    return record("chair", "chair", thread, "chair-ruled", path=path, **fields)


def _rows(path: Path | None) -> list[dict[str, object]]:
    src = path or telemetry_path()
    if not src.is_file():
        return []
    out: list[dict[str, object]] = []
    try:
        lines = src.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("role-telemetry: unreadable %s: %s", src, exc)
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("role-telemetry: skipping malformed line")
    return out


def chair_latency_seconds(thread: str, *, path: Path | None = None) -> float | None:
    """Seconds from a thread's ``digest-posted`` to its ``chair-ruled``.

    Derived at read time from the first matching pair; ``None`` when
    either endpoint is missing (an unruled digest has no latency —
    that absence IS the P4 signal, never coerced to a number).
    """
    posted: datetime | None = None
    for row in _rows(path):
        if row.get("thread") != thread:
            continue
        stamp = str(row.get("at", ""))
        try:
            at = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if row.get("event") == "digest-posted" and posted is None:
            posted = at
        elif row.get("event") == "chair-ruled" and posted is not None:
            return (at - posted).total_seconds()
    return None
