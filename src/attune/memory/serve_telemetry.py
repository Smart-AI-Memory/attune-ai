"""Curated serve telemetry — per-stem recall events (P3 task 2, D8).

The D8 measurement found the telemetry PIPE healthy but blind to the
curated tier: no event names a curated memory stem, so R6's ranking
term ("staleness × how often the memory is actually served") had no
data source. This module is the src-side emitter that closes that gap
for the in-repo serving surfaces (``PersonalMemory.query`` and
``recall_digest``); the SessionStart hydration emitter is personal
infra and is P3 task 3.

Writes the SAME sink the memory hooks use
(``$ATTUNE_HOME/telemetry/memory_events.jsonl``) with the same envelope
(``v``/``ts``/``event``), so the task-4 ``serve_counts`` reader — and
every existing consumer — parses one stream. The event is a COUNTER,
never a copy: stems only, no memory content.

Best-effort by contract: telemetry must never cost a caller their
recall result. Any failure degrades to ``False``.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

#: Event name for a curated-tier serve. Distinct from the raw-tier
#: ``session_recall`` so per-tier frequency never conflates the two.
CURATED_RECALL_EVENT = "curated_recall"

#: Cap on stems carried per event — a serve is bounded by the query's
#: ``k`` in practice; this is a malformed-caller backstop, not a policy.
MAX_STEMS_PER_EVENT = 50

_FALSEY = {"", "0", "false", "no", "off"}


def _enabled() -> bool:
    """False when local memory telemetry is switched off via env.

    Mirrors the hook-side writer exactly (``ATTUNE_MEMORY_TELEMETRY``
    off-switch plus ``DO_NOT_TRACK``) so one setting governs both
    writers of the shared sink.
    """
    if os.environ.get("ATTUNE_MEMORY_TELEMETRY", "1").strip().lower() in _FALSEY:
        return False
    dnt = os.environ.get("DO_NOT_TRACK")
    return dnt is None or dnt.strip().lower() in _FALSEY


def _events_path() -> Path:
    """The shared live events file under ``ATTUNE_HOME`` (default ``~/.attune``)."""
    home = os.environ.get("ATTUNE_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".attune"
    return base / "telemetry" / "memory_events.jsonl"


def log_curated_recall(stems: Sequence[str], surface: str, session_id: str | None = None) -> bool:
    """Append one ``curated_recall`` event naming the served stems.

    Args:
        stems: Filename stems of the curated memories served.
        surface: Which surface served them (``personal_query`` /
            ``recall_digest`` / ...).
        session_id: Originating session, when the caller knows it.

    Returns:
        True when a record was written; False when telemetry is off,
        there was nothing to record, or the write failed (fail-open).
    """
    try:
        clean = [str(s) for s in stems if s][:MAX_STEMS_PER_EVENT]
        if not clean or not _enabled():
            return False
        record: dict[str, object] = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event": CURATED_RECALL_EVENT,
            "surface": surface,
            "stems": clean,
            "entries": len(clean),
        }
        if session_id:
            record["session_id"] = str(session_id)[:64]
        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        validated = _validate_file_path(str(path), allowed_dir=str(path.parent))
        # One buffered write per record — appends of a single line are
        # effectively atomic, so concurrent sessions never interleave.
        line = json.dumps(record, separators=(",", ":"), default=str) + "\n"
        with validated.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return True
    except Exception as exc:  # noqa: BLE001 — telemetry never costs the recall
        logger.debug("curated_recall telemetry skipped: %s: %s", type(exc).__name__, exc)
        return False
