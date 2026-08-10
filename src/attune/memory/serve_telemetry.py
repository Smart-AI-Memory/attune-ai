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
from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
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


def serve_counts(
    window_days: int = 30,
    events_path: Path | None = None,
    today: date | None = None,
) -> dict[str, int]:
    """Per-stem curated serve counts over a trailing window (P3 task 4).

    The read half of the R6 frequency term: parses ``curated_recall``
    events from the shared sink — including rotated siblings
    (``memory_events.<date>.jsonl``), since a 30-day window can span the
    writer's size-rotation — and counts one serve per stem occurrence.

    Fail-open everywhere: a missing sink, unreadable file, malformed
    line, or unparseable timestamp contributes nothing rather than
    raising — an empty result means "no evidence", which ranking treats
    as never-served, the same honest floor the age side uses for
    ``mtime``.

    Args:
        window_days: Trailing window size; events older than this are
            excluded.
        events_path: Sink override for tests; defaults to the shared
            live sink under ``ATTUNE_HOME``.
        today: Reference date; defaults to the current date.

    Returns:
        ``{stem: serve_count}`` for every stem seen in the window.
    """
    path = events_path or _events_path()
    reference = today or date.today()
    cutoff = reference - timedelta(days=window_days)
    counts: Counter[str] = Counter()
    candidates = [path]
    try:
        candidates.extend(
            sibling
            for sibling in sorted(path.parent.glob(f"{path.stem}.*{path.suffix}"))
            if sibling != path
        )
    except OSError:
        pass  # a missing parent dir just means no rotated siblings
    for candidate in candidates:
        try:
            raw = candidate.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("unreadable events file %s: %s", candidate, exc)
            continue
        for line in raw.splitlines():
            if line.strip():
                counts.update(_stems_in_window(line, cutoff, reference))
    return dict(counts)


def _stems_in_window(line: str, cutoff: date, reference: date) -> list[str]:
    """Stems from one JSONL line, when it is an in-window curated event.

    Every malformed shape fails open to ``[]``: undecodable JSON,
    valid-but-non-object JSON (``[]``, ``"x"`` — codex D11 finding), a
    non-curated event, or an unparseable timestamp. The window is
    bounded BOTH ends — future-dated events (bad clocks, corrupt
    timestamps) are excluded, and the lower bound is exclusive so
    ``window_days=30`` covers exactly 30 calendar dates ending
    ``reference`` (codex D11 findings).
    """
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return []
    if not isinstance(record, dict) or record.get("event") != CURATED_RECALL_EVENT:
        return []
    try:
        when = date.fromisoformat(str(record.get("ts", ""))[:10])
    except ValueError:
        return []
    if when <= cutoff or when > reference:
        return []
    return [stem for stem in record.get("stems") or [] if isinstance(stem, str) and stem]
