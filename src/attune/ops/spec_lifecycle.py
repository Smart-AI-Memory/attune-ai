"""Lifecycle bucket derivation for spec records.

Pure logic — takes a SpecRecord-like object (any object with ``.phases``
and ``.last_modified`` attributes) and returns one of seven bucket labels:
``paused``, ``parked``, ``complete``, ``stale``, ``draft``,
``approved-not-shipped``, ``active``. (``parked`` added 2026-07-20,
q-briefing-triage-002 A2 — chair parks were previously invisible and
mis-bucketed as approved-not-shipped drift.)

The 6-rule cascade (first-match-wins) matches the spec at
[docs/specs/ops-specs-page-refinement/decisions.md](../../../docs/specs/ops-specs-page-refinement/decisions.md)
§ "Lifecycle derivation algorithm". Pre-committed there before this
implementation landed, per the existing "Pre-committed decision matrices
survive contact with data" lesson.

Stale threshold is a module-level constant (30 days, ratified
2026-05-31). Module is pure — no I/O, no project-root awareness. Callers
build SpecRecord objects via ``routes/specs.py`` and pass them here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

# 30-day stale threshold. Ratified 2026-05-31 in decisions.md D1.
# Revisit if 30d proves too noisy or too quiet in practice.
STALE_THRESHOLD_DAYS: int = 30

# Statuses we treat as "the phase is done." `shipped` closes a spec
# whose deliverable landed; `superseded` closes one another spec
# replaced (both terminal — ratified 2026-07-20, q-briefing-triage-002).
_COMPLETE_STATUSES: frozenset[str] = frozenset(
    {"complete", "completed", "done", "shipped", "superseded"}
)

# Statuses we treat as "the phase is approved." Includes complete-
# equivalents plus the in-flight tokens (`active`, `living`) so they
# clear the draft rule.
_APPROVED_STATUSES: frozenset[str] = frozenset(
    _COMPLETE_STATUSES | {"approved", "active", "living"}
)

#: The full recognized status vocabulary (leading token after
#: `_normalize`). The status-line baseline gate
#: (`attune.gates.lifecycle.status_line`) enforces membership; keep
#: the two in one place. `parked` REQUIRES a `Resume-Trigger:` clause
#: in the same file (R9, q-briefing-triage-001).
STATUS_VOCABULARY: frozenset[str] = frozenset(_APPROVED_STATUSES | {"draft", "parked", "paused"})


@runtime_checkable
class _PhaseLike(Protocol):
    """Structural protocol for a SpecPhase-like object."""

    name: str
    exists: bool
    status: str | None


@runtime_checkable
class _SpecLike(Protocol):
    """Structural protocol for a SpecRecord-like object."""

    phases: list[_PhaseLike]
    last_modified: str | None


def derive_lifecycle(spec: _SpecLike, *, now: datetime | None = None) -> str:
    """Return the lifecycle bucket label for one spec.

    Args:
        spec: Object with ``.phases`` (list of SpecPhase-like) and
            ``.last_modified`` (ISO-8601 string or ``None``).
        now: Optional override for "current time" — for deterministic
            testing. Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        One of: ``paused``, ``parked``, ``complete``, ``stale``,
        ``draft``, ``approved-not-shipped``, ``active``. Always
        returns a value; never raises.

    Cascade (first match wins):
        1. **paused** — ANY phase status contains "paused"
           (case-insensitive). Explicit pause signal wins everything.
        1b. **parked** — ANY phase status has leading token "parked"
           (a chair park; R9 requires a ``Resume-Trigger:`` clause,
           enforced by the status-line gate, not here).
        2. **complete** — every phase that EXISTS has a status in
           ``_COMPLETE_STATUSES``, AND at least one phase exists. Note:
           the spec doc says "ALL 4 phases" but real specs sometimes ship
           with 3 phase files (no ``decisions.md``); treating non-existent
           phases as not-blocking matches author intent for those cases.
        2b. **active** (via ``living``) — ANY phase status has leading
           token "living": an evergreen program, never a rot alarm.
        3. **stale** — ``last_modified`` is older than
           ``STALE_THRESHOLD_DAYS``. Wins over Draft/Approved-not-shipped/
           Active so users see "rotting" instead of nominal state.
        4. **draft** — ``requirements.md`` missing OR its status is NOT
           in ``_APPROVED_STATUSES``.
        5. **approved-not-shipped** — ``requirements.md`` leading token
           is exactly "approved" AND ``tasks.md`` exists AND no phase
           has a complete-status. The in-flight tokens
           (``active``/``living``/``shipped``) skip this alarm bucket.
        6. **active** — default.
    """
    # 1. Paused — explicit signal wins everything
    for phase in spec.phases:
        if phase.status and "paused" in phase.status.lower():
            return "paused"

    # 1b. Parked — an explicit chair park (leading token, so prose
    # mentions of "parked" in annotations don't trip it). Requires a
    # Resume-Trigger clause per R9; the status-line gate enforces that.
    for phase in spec.phases:
        if phase.status and _normalize(phase.status) == "parked":
            return "parked"

    # 2. Complete — every existing phase is done, at least one exists
    existing = [p for p in spec.phases if p.exists]
    if existing and all(
        p.status is not None and _normalize(p.status) in _COMPLETE_STATUSES for p in existing
    ):
        return "complete"

    # 2b. Living — an evergreen program (test-quality-program class):
    # deliberately never "complete", never a rot alarm.
    for phase in spec.phases:
        if phase.status and _normalize(phase.status) == "living":
            return "active"

    # 3. Stale — last_modified older than threshold
    if _is_stale(spec.last_modified, now=now):
        return "stale"

    phase_by_name = {p.name: p for p in spec.phases}

    # 4. Draft — requirements missing OR not approved
    requirements = phase_by_name.get("requirements")
    if (
        requirements is None
        or not requirements.exists
        or requirements.status is None
        or _normalize(requirements.status) not in _APPROVED_STATUSES
    ):
        return "draft"

    # 5. Approved-not-shipped — requirements token is exactly
    # "approved" (the in-flight tokens `active`/`living`/`shipped`
    # deliberately skip this alarm bucket) + tasks.md exists + no
    # phase marked complete
    tasks = phase_by_name.get("tasks")
    has_tasks = tasks is not None and tasks.exists
    any_complete = any(
        p.status is not None and _normalize(p.status) in _COMPLETE_STATUSES for p in spec.phases
    )
    if _normalize(requirements.status) == "approved" and has_tasks and not any_complete:
        return "approved-not-shipped"

    # 6. Active — default
    return "active"


def _normalize(status: str) -> str:
    """Lowercase + strip the status string for set-membership checks.

    Real-world statuses often carry annotations like ``complete (2026-05-10)``
    or ``approved (2026-05-31; see decisions.md)``. We compare the leading
    token before any whitespace or punctuation. Custom strings like ``partial``
    fall through and don't match any known set.
    """
    head = status.strip().lower()
    # Split on whitespace, parenthesis, comma — take the leading word
    for sep in (" ", "(", ",", ";", "—", "-"):
        idx = head.find(sep)
        if idx >= 0:
            head = head[:idx]
    return head.strip()


def _is_stale(last_modified: str | None, *, now: datetime | None = None) -> bool:
    """Return True if ``last_modified`` is older than
    ``STALE_THRESHOLD_DAYS``.

    Tolerates both naive and timezone-aware ISO strings (defensive default
    to UTC). Returns False on parse errors or missing input — staleness is
    additive evidence, not a default state.
    """
    if not last_modified:
        return False
    try:
        ts = datetime.fromisoformat(last_modified)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current - ts) > timedelta(days=STALE_THRESHOLD_DAYS)
