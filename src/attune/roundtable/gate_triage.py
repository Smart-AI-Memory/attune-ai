"""Gate-triage inbox — round-table P2 (issue #1587).

Ruled 2026-07-21 (thread ``q-roundtable-extensions-001``, chair:
Patrick; recorded in docs/specs/spec-lifecycle-gates/decisions.md).
V1 shape, verbatim from the ruling:

- **READ-ONLY** over the G1 verdict ledger — groups unresolved
  ``CHAIR_REQUIRED`` receipts by ``(target, gate_id)``. Never
  appends to the ledger, never alters gate state (RR-2).
- Convenes **ONE D3-capped mini-table** ONLY past a threshold
  (``N >= 3`` pending OR oldest ``> 48h``). Below threshold the
  inbox is a quiet grouped listing with **no board writes** — the
  ruled failure mode is inbox ceremony: a meeting queue noisier
  than the raw ledger.
- Emits **one disposition per shortfall group** from a CLOSED enum
  (:data:`TRIAGE_DISPOSITIONS`); a reply that names none records as
  ``no-recommendation`` — TAC-4, never laundered into a
  recommendation.
- Appends a **single chair digest**; marks deliberated receipts
  triaged in its own state file (**dedup mandatory** — a triaged
  ``receipt_id`` is never re-deliberated).
- **RR-4 risk tiers govern eligibility from day one**: only
  receipts whose ``gate_id`` is in the known inventory
  (``LADDER_GATES``, the RR-4 superset) are deliberation-eligible;
  unknown gates are NAMED for the chair, never silently dropped.
- **P3 skeptic dissents route into this digest** (one chair inbox)
  as duck-typed mappings — no import of the skeptic module.

P4 role telemetry (record-only) starts recording with this launch:
each pass records seat invocations and the digest post, giving
chair-latency its start timestamp.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from attune.gates.lifecycle.ledger import unresolved_chair_required
from attune.gates.lifecycle.protocol import GateReceipt
from attune.roundtable import role_telemetry
from attune.roundtable.rotation import CANONICAL_SEATS

logger = logging.getLogger(__name__)

#: Convene threshold (the ruling, verbatim): N pending receipts …
THRESHOLD_PENDING = 3
#: … OR the oldest pending receipt is older than this.
THRESHOLD_OLDEST_HOURS = 48

#: D3 — up to 3 invocations for the one mini-table sitting
#: (agent-round-table D3; same ceiling semantic as the P3 skeptic).
TABLE_MAX_INVOCATIONS = 3

#: CLOSED disposition enum — one per shortfall group. Extending it
#: is a spec amendment (the gate-protocol STATES discipline).
TRIAGE_DISPOSITIONS: tuple[str, ...] = ("uphold", "waive", "revise", "defer")

#: The recorded value when the table sat but named no valid
#: disposition for a group — chair-visible, never a member of the
#: enum, never laundered.
NO_RECOMMENDATION = "no-recommendation"

_DISPOSITION_RE = re.compile(
    r"^\s*DISPOSITION:\s*(?P<target>[^:]+?)\s*::\s*(?P<gate>[^:]+?)"
    r"\s*::\s*(?P<disposition>[a-z-]+)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Shortfall:
    """One deliberation unit: every pending receipt for a spec+gate."""

    target: str
    gate_id: str
    receipts: tuple[GateReceipt, ...]

    @property
    def oldest(self) -> str:
        return min(r.timestamp for r in self.receipts)


@dataclass
class TriageRecord:
    """One complete inbox pass — everything the chair digest needs."""

    shortfalls: list[Shortfall] = field(default_factory=list)
    ineligible: list[GateReceipt] = field(default_factory=list)
    dispositions: dict[tuple[str, str], str] = field(default_factory=dict)
    dissents: list[Mapping[str, object]] = field(default_factory=list)
    outcome: str = "pending"
    seat: str | None = None
    invocations: int = 0
    thread: str = ""


def state_path() -> Path:
    """``<ATTUNE_HOME|~/.attune>/ops/gates/triage_state.json``."""
    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    return attune_dir / "ops" / "gates" / "triage_state.json"


def load_triaged(*, path: Path | None = None) -> dict[str, dict[str, str]]:
    """``receipt_id -> {thread, at, disposition}`` for every triaged receipt."""
    src = path or state_path()
    if not src.is_file():
        return {}
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("gate-triage: unreadable state %s: %s — treating as empty", src, exc)
        return {}
    return data if isinstance(data, dict) else {}


def mark_triaged(entries: Mapping[str, dict[str, str]], *, path: Path | None = None) -> Path:
    """Merge ``entries`` into the triage state file (dedup ledger)."""
    dest = path or state_path()
    state = load_triaged(path=dest)
    state.update({k: dict(v) for k, v in entries.items()})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return dest


def eligible_gate_ids() -> tuple[str, ...]:
    """The RR-4 gate inventory that governs triage eligibility."""
    from attune.gates.lifecycle.activation import LADDER_GATES

    return LADDER_GATES


def collect_shortfalls(
    *,
    ledger_path: Path | None = None,
    triage_state_path: Path | None = None,
) -> tuple[list[Shortfall], list[GateReceipt]]:
    """Group unresolved, untriaged CHAIR_REQUIRED receipts (read-only).

    Returns ``(shortfalls, ineligible)`` — a receipt whose gate is
    outside the RR-4 inventory is returned separately so the digest
    can NAME it for the chair rather than silently dropping it.
    """
    triaged = load_triaged(path=triage_state_path)
    known = set(eligible_gate_ids())
    groups: dict[tuple[str, str], list[GateReceipt]] = {}
    ineligible: list[GateReceipt] = []
    for receipt in unresolved_chair_required(path=ledger_path):
        if receipt.receipt_id in triaged:
            continue  # dedup mandatory — never re-deliberate
        if receipt.gate_id not in known:
            ineligible.append(receipt)
            continue
        groups.setdefault((receipt.target, receipt.gate_id), []).append(receipt)
    shortfalls = [
        Shortfall(target=t, gate_id=g, receipts=tuple(rs)) for (t, g), rs in sorted(groups.items())
    ]
    return shortfalls, ineligible


def past_threshold(shortfalls: Sequence[Shortfall], now: _dt.datetime | None = None) -> bool:
    """The ruled convene test: N >= 3 pending OR oldest > 48h."""
    pending = sum(len(s.receipts) for s in shortfalls)
    if pending == 0:
        return False
    if pending >= THRESHOLD_PENDING:
        return True
    now = now or _dt.datetime.now(_dt.timezone.utc)
    oldest = min(s.oldest for s in shortfalls)
    try:
        oldest_at = _dt.datetime.fromisoformat(oldest)
    except ValueError:
        return True  # unparseable age reads as stale, never as fresh
    if oldest_at.tzinfo is None:
        oldest_at = oldest_at.replace(tzinfo=_dt.timezone.utc)
    return (now - oldest_at) > _dt.timedelta(hours=THRESHOLD_OLDEST_HOURS)


def build_table_brief(shortfalls: Sequence[Shortfall]) -> str:
    """The R1 text-only brief for the one mini-table sitting."""
    blocks = []
    for s in shortfalls:
        findings = "\n".join(f"- {f}" for r in s.receipts for f in r.findings) or "- (none)"
        blocks.append(
            f"### {s.target} :: {s.gate_id} "
            f"({len(s.receipts)} receipt(s), oldest {s.oldest})\n{findings}"
        )
    choices = " | ".join(TRIAGE_DISPOSITIONS)
    return (
        "You are one seat of a gate-triage mini-table. The shortfall "
        "groups below are unresolved CHAIR_REQUIRED gate receipts. "
        "For EACH group, recommend exactly one disposition for the "
        "chair. You never alter gate state; the chair rules.\n\n"
        "Reply with one line per group, EXACTLY:\n\n"
        f"DISPOSITION: <target> :: <gate_id> :: <{choices}>\n"
        "REASON: <one line>\n\n"
        "Calibration: an evidence-free 'waive' is rubber-stamp decay; "
        "a 'defer' on every group is inbox ceremony. Ground each "
        "recommendation in the group's findings. Text only.\n\n" + "\n\n".join(blocks)
    )


def parse_dispositions(text: str, shortfalls: Sequence[Shortfall]) -> dict[tuple[str, str], str]:
    """One disposition per shortfall group, from the closed enum.

    Groups the reply skips, misnames, or grades outside the enum
    record :data:`NO_RECOMMENDATION` — visible to the chair, never
    invented and never laundered.
    """
    named: dict[tuple[str, str], str] = {}
    for m in _DISPOSITION_RE.finditer(text):
        key = (m.group("target").strip(), m.group("gate").strip())
        disposition = m.group("disposition").strip()
        if disposition in TRIAGE_DISPOSITIONS:
            named[key] = disposition
    return {
        (s.target, s.gate_id): named.get((s.target, s.gate_id), NO_RECOMMENDATION)
        for s in shortfalls
    }


def run_triage(
    board: object | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    seat_recipes: Sequence[tuple[str, tuple[str, ...]]] | None = None,
    dissents: Sequence[Mapping[str, object]] = (),
    thread: str | None = None,
    ledger_path: Path | None = None,
    triage_state_path: Path | None = None,
    telemetry_path: Path | None = None,
    now: _dt.datetime | None = None,
) -> TriageRecord:
    """Run ONE inbox pass; return the record.

    Below threshold: read-only grouping, NO board writes, no seat
    spend. Past threshold: one D3-capped mini-table, one digest,
    receipts marked triaged. Never alters gate state (RR-2/R8).
    ``dissents`` are duck-typed P3 skeptic dissent records
    (mappings with ``spec``/``cite``/``reason``) routed into the
    same digest.
    """
    record = TriageRecord(dissents=list(dissents))
    record.shortfalls, record.ineligible = collect_shortfalls(
        ledger_path=ledger_path, triage_state_path=triage_state_path
    )
    stamp = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%d-%H%M")
    record.thread = thread or f"gate-triage-{stamp}"

    if not past_threshold(record.shortfalls, now=now) and not record.dissents:
        record.outcome = "below-threshold"
        return record

    if record.shortfalls and not _convene(record, board, invoke_seat, seat_recipes, telemetry_path):
        return record

    _mark_deliberated(record, triage_state_path)
    _post(board, record.thread, "moderator", "synthesis", digest(record))
    role_telemetry.record(
        "moderator", "moderator", record.thread, "digest-posted", path=telemetry_path
    )
    if record.outcome == "pending":
        record.outcome = "digested"
    return record


def _convene(
    record: TriageRecord,
    board: object | None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None,
    seat_recipes: Sequence[tuple[str, tuple[str, ...]]] | None,
    telemetry_path: Path | None,
) -> bool:
    """The ONE mini-table sitting — returns False when no seat sat."""
    from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

    invoke = invoke_seat or default_invoke_seat
    recipes = dict(seat_recipes or SEAT_RECIPES)
    brief = build_table_brief(record.shortfalls)
    _post(board, record.thread, "moderator", "question", brief)

    for seat in [s for s in CANONICAL_SEATS if s in recipes]:
        if record.invocations >= TABLE_MAX_INVOCATIONS:
            break
        record.invocations += 1
        role_telemetry.record("triage-seat", seat, record.thread, "invoked", path=telemetry_path)
        code, reply = invoke(recipes[seat], brief)
        if code != 0 or not reply.strip():
            _post(
                board,
                record.thread,
                seat,
                "position",
                f"ABSENT — exit {code}: {reply[:200]}",
                absent=True,
            )
            role_telemetry.record("triage-seat", seat, record.thread, "absent", path=telemetry_path)
            continue
        record.seat = seat
        record.dispositions = parse_dispositions(reply, record.shortfalls)
        _post(board, record.thread, seat, "position", reply)
        role_telemetry.record("triage-seat", seat, record.thread, "replied", path=telemetry_path)
        break

    if record.seat is None:
        record.outcome = "table-absent"
        _post(
            board,
            record.thread,
            "moderator",
            "halt",
            "no triage seat reachable; receipts stay pending; chair reviews unassisted",
        )
        return False
    record.outcome = "deliberated"
    return True


def _mark_deliberated(record: TriageRecord, triage_state_path: Path | None) -> None:
    """Mark every deliberated receipt triaged (dedup — never re-deliberate)."""
    if record.seat is None or not record.dispositions:
        return
    at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    entries = {
        r.receipt_id: {
            "thread": record.thread,
            "at": at,
            "disposition": record.dispositions[(s.target, s.gate_id)],
        }
        for s in record.shortfalls
        for r in s.receipts
    }
    mark_triaged(entries, path=triage_state_path)


def digest(record: TriageRecord) -> str:
    """The single chair digest for one pass."""
    lines = [f"Gate-triage digest ({record.thread}): outcome={record.outcome}"]
    for s in record.shortfalls:
        disposition = record.dispositions.get((s.target, s.gate_id), "pending")
        lines.append(
            f"{s.target} :: {s.gate_id} — {len(s.receipts)} receipt(s), "
            f"recommended: {disposition}"
        )
    if record.ineligible:
        named = "; ".join(f"{r.target}::{r.gate_id}" for r in record.ineligible)
        lines.append(f"ineligible (gate outside the RR-4 inventory — chair-only): {named}")
    for d in record.dissents:
        lines.append(
            f"P3 skeptic DISSENT on {d.get('spec', '?')!r}: cite={d.get('cite', '?')}; "
            f"reason={d.get('reason', '(none)')}"
        )
    lines.append("Chair rules; this pass never alters gate state (RR-2/R8).")
    return "\n".join(lines)


def _post(
    board: object | None, thread: str, seat: str, kind: str, body: str, **fields: object
) -> None:
    """Post to the board when one is wired; print otherwise."""
    if board is None:
        print(f"[{thread}] {seat}/{kind}: {body[:160]}", flush=True)
        return
    board.post_message(thread, seat, kind, body, **fields)  # type: ignore[attr-defined]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m attune.roundtable.gate_triage [--dry-run]``.

    ``--dry-run`` prints the grouped inbox and threshold verdict
    without any board write or seat invocation.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Gate-triage inbox pass over unresolved CHAIR_REQUIRED receipts (P2)."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    shortfalls, ineligible = collect_shortfalls()
    if args.dry_run:
        convene = past_threshold(shortfalls)
        print(f"pending shortfall groups: {len(shortfalls)}; convene={convene}")
        for s in shortfalls:
            print(f"  {s.target} :: {s.gate_id} — {len(s.receipts)} receipt(s), oldest {s.oldest}")
        for r in ineligible:
            print(f"  ineligible: {r.target} :: {r.gate_id} (outside RR-4 inventory)")
        return 0

    from attune.roundtable.board import Board

    record = run_triage(board=Board())
    print(f"gate-triage pass complete: outcome={record.outcome}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
