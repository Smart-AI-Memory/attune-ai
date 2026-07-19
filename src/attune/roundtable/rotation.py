"""Rotation algorithm + baseline eligibility — round-table V2-P4.

Implements RR-2 (owed-pointer rotation over the canonical seat
order) and RR-4 (baseline eligibility computed from chair-attested
structured lines in the owning spec's ``decisions.md``; activation
only by an explicit chair arming ruling) from
``docs/specs/roundtable-producing-team/p4-requirements.md``
(thread ``table-p4-001``).

The pointer function is pure over the ledger (RR-1's durable store,
``Board.ledger_read``): no configuration input other than the
canonical seat order, no clock, no I/O.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

#: Canonical seat order (RR-2) — the ``SEAT_RECIPES`` order.
CANONICAL_SEATS: tuple[str, ...] = ("claude", "antigravity", "codex")

#: Fixed-roles assignment (PACK-1 / chair ruling 2026-07-18), in
#: force until the chair arms rotation (RR-4).
FIXED_DRAFTER = "claude"

#: RR-4 structured lines in decisions.md — chair-attested baseline
#: evidence and the explicit arming ruling.
_BASELINE_RE = re.compile(
    r"^P4-BASELINE:\s*thread=(?P<thread>\S+)\s+promoted=(?P<promoted>\S+)"
    r"\s+downstream=(?P<downstream>\S+)\s*$",
    re.MULTILINE,
)
_ARMED_RE = re.compile(r"^P4-ROTATION:\s*armed\b.*$", re.MULTILINE)
_P4_LINE_RE = re.compile(r"^P4-(?:BASELINE|ROTATION):.*$", re.MULTILINE)


def next_owed(records: Sequence[Mapping[str, object]]) -> str:
    """Return the seat owed the next drafter turn (RR-2, pure).

    The pointer advances past a seat only when that seat has actually
    served as drafter: if the most recent ledger record has
    ``owed_seat == actual_drafter`` and ``served`` true, the next
    owed seat is the one after it in canonical order; otherwise the
    owed seat is unchanged (substitute service and failed runs never
    advance the pointer).
    """
    if not records:
        return CANONICAL_SEATS[0]
    last = records[-1]
    owed = str(last.get("owed_seat", ""))
    if owed not in CANONICAL_SEATS:
        raise ValueError(f"ledger record has unknown owed_seat: {owed!r}")
    if bool(last.get("served")) and last.get("actual_drafter") == owed:
        return CANONICAL_SEATS[(CANONICAL_SEATS.index(owed) + 1) % len(CANONICAL_SEATS)]
    return owed


def assignments_for(drafter: str) -> dict[str, str]:
    """Return the full seat→role mapping for a drafter (RR-2).

    Critic roles are derived (the two non-drafter seats) but named
    explicitly so downstream consumers never re-derive them.
    """
    if drafter not in CANONICAL_SEATS:
        raise ValueError(f"unknown seat: {drafter!r}")
    return {seat: ("drafter" if seat == drafter else "critic") for seat in CANONICAL_SEATS}


@dataclass
class RotationStatus:
    """The RR-4 eligibility report — evidence, never a bare boolean."""

    state: str  # not_eligible | eligible_unarmed | armed
    baselines: list[dict[str, str]] = field(default_factory=list)
    armed_line: str | None = None
    problems: list[str] = field(default_factory=list)


def rotation_status(decisions_text: str) -> RotationStatus:
    """Compute rotation eligibility from decisions.md text (RR-4).

    Eligibility = at least two ``P4-BASELINE:`` lines, of which at
    least one carries a non-``pending`` downstream ref. Activation is
    never automatic: the state is ``armed`` only when an explicit
    ``P4-ROTATION: armed`` chair ruling exists. Malformed ``P4-``
    lines are reported as problems, never guessed at. No count of
    rounds, invocations, critiques, or agreement rate appears here
    (TR-9 guard).
    """
    baselines = [m.groupdict() for m in _BASELINE_RE.finditer(decisions_text)]
    armed = _ARMED_RE.search(decisions_text)
    recognized = {m.group(0).strip() for m in _BASELINE_RE.finditer(decisions_text)}
    if armed:
        recognized.add(armed.group(0).strip())
    problems = [
        line.strip()
        for line in (m.group(0) for m in _P4_LINE_RE.finditer(decisions_text))
        if line.strip() not in recognized
    ]
    eligible = len(baselines) >= 2 and any(b["downstream"] != "pending" for b in baselines)
    if armed:
        state = "armed"
    elif eligible:
        state = "eligible_unarmed"
    else:
        state = "not_eligible"
    return RotationStatus(
        state=state,
        baselines=baselines,
        armed_line=armed.group(0).strip() if armed else None,
        problems=problems,
    )
