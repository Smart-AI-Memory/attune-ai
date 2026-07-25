"""Local-only log of form-surface routing decisions.

The decay guard for D21 (round table ``q-forms-default-vs-latency-001``,
Claude seat): flipping the default to the rich widget is only worth
something if the behaviour actually changes, so record what
:func:`attune.elicitation.select_form_surface` decided and let a later
read answer "did the mix move?" instead of assuming it did.

One event = one JSON line: ``v`` / ``ts`` / ``event`` / ``surface``
plus optional routing context.

**What this can and cannot measure.** The live call site is the pair of
MCP elicitation handlers, where the tool the agent invoked *is* its
choice — so each record carries the router's recommendation (``surface``
/ ``reason``), what the agent actually did (``chosen``), and whether
they matched (``agreed``). That makes disagreement visible, not just
volume.

It still does NOT see a raw ``AskUserQuestion`` turn the agent wrote by
hand without building a ``FormSchema`` at all — that path never enters
Python. So the forms-vs-no-form ratio remains only partially observable
from here, and the missing half has to come from transcript inspection.
What *is* now observable is the narrower and more actionable signal:
when a form was built and the agent then flattened it anyway.

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


#: Form submissions before the one-time keyboard-mode hint fires. D17
#: ratified usage-triggered discovery ("after N form submissions"), not a
#: calendar timer — someone who never feels the friction never sees it.
_HINT_AFTER_SUBMISSIONS = 10

#: Shown to a user who has answered enough forms to have an opinion.
_KEYBOARD_HINT = (
    "You've answered several forms. If you'd rather answer with the "
    "keyboard than the mouse, turn on keyboard mode — "
    "`attune config set keyboard_mode true` — and asks that fit a plain "
    "question will come back as button turns instead of forms."
)


def log_submission() -> None:
    """Record that a user submitted a form. Best-effort, never raises."""
    try:
        if not _enabled():
            return
        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _rotate_if_huge(path)
        record = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event": "form_submitted",
        }
        with path.open("a", encoding="utf-8") as fh:
            json.dump(record, fh, separators=(",", ":"))
            fh.write("\n")
    except OSError:
        pass


def _hint_marker() -> Path:
    """Path of the once-only marker for the keyboard-mode hint."""
    return _events_path().with_name("keyboard_hint_shown")


def maybe_keyboard_hint(keyboard_mode: bool = False) -> str | None:
    """Return the keyboard-mode hint the first time it is earned, else None.

    Fires at most once ever, only after the user has actually answered
    :data:`_HINT_AFTER_SUBMISSIONS` forms, and never when they already
    have keyboard mode on. Writes the marker before returning so a caller
    that fires twice in one session still only shows it once.

    Args:
        keyboard_mode: Whether the user has already opted in.

    Returns:
        The hint text, or ``None``.
    """
    try:
        if keyboard_mode or not _enabled():
            return None
        marker = _hint_marker()
        if marker.exists():
            return None
        if submission_count() < _HINT_AFTER_SUBMISSIONS:
            return None
        marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker.write_text("shown\n", encoding="utf-8")
        return _KEYBOARD_HINT
    except OSError:
        return None


def submission_count() -> int:
    """Number of form submissions recorded in the live log."""
    count = 0
    try:
        with _events_path().open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get("event") == "form_submitted":
                    count += 1
    except OSError:
        return 0
    return count


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
