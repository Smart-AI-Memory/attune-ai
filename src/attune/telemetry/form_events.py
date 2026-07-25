"""Local-only log of form-surface routing decisions.

The decay guard for D21 (round table ``q-forms-default-vs-latency-001``,
Claude seat): flipping the default to the rich widget is only worth
something if the behaviour actually changes, so record what
:func:`attune.elicitation.select_form_surface` decided and let a later
read answer "did the mix move?" instead of assuming it did.

One event = one JSON line: ``v`` / ``ts`` / ``event`` / ``surface``
plus optional routing context.

**What this can and cannot measure.** It sees every form that reaches
the router, so it measures the *surface mix* (widget vs ask) faithfully.
It does NOT see a raw ``AskUserQuestion`` turn the agent wrote by hand
without building a ``FormSchema`` — that path never enters Python. So
this instruments routing, not firing; the forms-vs-raw-turns ratio the
round table asked for is only partially observable from here, and the
missing half has to come from transcript inspection.

Consent model matches :mod:`attune.telemetry.memory_events`: LOCAL
recording is default-on and nothing ever leaves the machine.
``DO_NOT_TRACK`` or ``ATTUNE_FORM_TELEMETRY=0`` disables the log.
Never raises — routing must not fail because telemetry did.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_FALSEY = {"", "0", "false", "no", "off"}

#: Rotate when the live file exceeds this. Mirrors ``memory_events``.
_MAX_BYTES = 5 * 1024 * 1024


def _enabled() -> bool:
    """False when local form telemetry is switched off via env."""
    if os.environ.get("ATTUNE_FORM_TELEMETRY", "1").strip().lower() in _FALSEY:
        return False
    dnt = os.environ.get("DO_NOT_TRACK")
    return dnt is None or dnt.strip().lower() in _FALSEY


def _events_path() -> Path:
    """Resolve the live events file under ATTUNE_HOME (default ~/.attune)."""
    home = os.environ.get("ATTUNE_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".attune"
    return base / "telemetry" / "form_events.jsonl"


def _rotate_if_huge(path: Path) -> None:
    """Best-effort size backstop: rotate to a dated sibling when huge."""
    try:
        if path.stat().st_size < _MAX_BYTES:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rotated = path.with_name(f"form_events.{stamp}.jsonl")
        counter = 1
        while rotated.exists():
            rotated = path.with_name(f"form_events.{stamp}.{counter}.jsonl")
            counter += 1
        path.replace(rotated)
    except OSError:
        pass  # rotation is a nicety; the append below still works


def log_surface_decision(surface: str, **fields: object) -> None:
    """Append one surface-routing decision. Best-effort, never raises.

    Args:
        surface: The chosen surface — ``"widget"`` or ``"ask"``.
        **fields: Routing context (e.g. ``reason``, ``question_count``).
    """
    try:
        if not _enabled():
            return
        record: dict[str, object] = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event": "form_surface",
            "surface": str(surface)[:32],
        }
        record.update(fields)

        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _rotate_if_huge(path)
        with path.open("a", encoding="utf-8") as fh:
            json.dump(record, fh, separators=(",", ":"), default=str)
            fh.write("\n")
    except OSError:
        pass  # telemetry is best-effort; never break the caller


def surface_mix() -> dict[str, int]:
    """Return counts per surface from the live log.

    Unreadable or malformed lines are skipped rather than raising, so a
    partially-written tail never breaks the read.

    Returns:
        A mapping of surface name to count; empty when nothing logged.
    """
    counts: Counter[str] = Counter()
    path = _events_path()
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get("event") == "form_surface":
                    counts[str(record.get("surface", "(unknown)"))] += 1
    except OSError:
        return {}
    return dict(counts)
