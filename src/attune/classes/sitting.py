"""The sitting — release-audit-stage R3 step 4.

One round, three seats, no rebuttal loop. The seats do NOT re-review the
diff: D3 settled that by measurement (450k tokens produced 8 instances
of a single class), so role (d) "detect defects" is OUT. What they do is
narrow and cheap:

* **(a)** advise SHIP/HOLD per residual item, by amending the packet's
  §7 pre-filled defaults **per item id**
* **(c)** rank which ungated/open classes most need a gate before this
  release

That is why the sitting is payable every release (D2): the seats read a
capped packet and amend a list, rather than composing an opinion from a
dump. R4 §7 is explicit — seats AMEND pre-filled dispositions, one
closing paragraph maximum.

An ABSENT seat is a valid outcome, never a fabricated one. A seat whose
reply does not parse is recorded as ``format_noncompliant`` with its raw
text preserved; the stage does not invent amendments on its behalf.

A seat that was never reachable (``absent``) and a seat that RAN and
FAILED (``failed``) are different facts and are recorded differently.
Conflating them cost three consecutive sittings: the ``claude`` seat's
OAuth session had expired, the CLI said so on stdout and exited 1, and
every run recorded a bare ``absent`` while discarding the diagnosis
(issue #2311). Every non-replied seat now carries a ``reason`` into
:meth:`SeatReply.as_dict`, so the emitted sitting states WHY a seat did
not speak. Contract principle 7 — a failed gatekeeper fails the gate;
absence is not a pass — applies to the seats themselves.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from attune.classes.packet import DISPOSITIONS, Packet

__all__ = [
    "SEATS",
    "SeatAmendment",
    "SeatReply",
    "Sitting",
    "build_sitting_brief",
    "compute_sitting_delta",
    "hold_sitting",
    "parse_seat_reply",
]

#: Three seats, one round (R3 step 4). Order is stable so a manifest's
#: recorded replies are comparable release over release.
SEATS: tuple[str, ...] = ("claude", "codex", "antigravity")

#: Reply budget. The packet is already capped; a seat that needs more
#: than this is composing rather than amending.
SEAT_REPLY_CHARS = 4000

#: How much of a non-replied seat's output is kept as its ``reason``.
#: Enough for a CLI's one-line diagnosis plus context, not a dump.
REASON_CHARS = 400

#: ``run_command`` maps a missing binary to 127 and a timeout to 124.
_EXIT_NOT_FOUND = 127

_AMEND = re.compile(
    r"^\s*AMEND\s+(?P<item>\S+)\s*->\s*(?P<disp>[A-Z-]+)\s*:\s*(?P<reason>.+?)\s*$",
    re.MULTILINE,
)
_RANK = re.compile(r"^\s*GATE-RANK\s*:\s*(?P<ranking>.+?)\s*$", re.MULTILINE)
_CLOSING = re.compile(r"^\s*CLOSING\s*:\s*(?P<text>.+?)\s*$", re.MULTILINE | re.DOTALL)
_NO_AMENDMENTS = re.compile(r"^\s*NO AMENDMENTS\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SeatAmendment:
    """One seat's proposed disposition for one residual item."""

    item_id: str
    disposition: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"item_id": self.item_id, "disposition": self.disposition, "reason": self.reason}


@dataclass(frozen=True)
class SeatReply:
    """What one seat said. ``status`` is never inferred as agreement."""

    seat: str
    status: str  # "replied" | "absent" | "failed" | "format_noncompliant"
    amendments: tuple[SeatAmendment, ...] = field(default=())
    gate_ranking: tuple[str, ...] = field(default=())
    closing: str = ""
    raw: str = ""

    def as_dict(self) -> dict[str, Any]:
        emitted: dict[str, Any] = {
            "seat": self.seat,
            "status": self.status,
            "amendments": [a.as_dict() for a in self.amendments],
            "gate_ranking": list(self.gate_ranking),
            "closing": self.closing,
        }
        # A seat that did not reply must say why. Dropping this is what
        # let an expired credential read as three silent absences.
        if self.status != "replied":
            emitted["reason"] = self.raw[:REASON_CHARS].strip()
        return emitted


@dataclass(frozen=True)
class Sitting:
    """One round of three seats over one packet."""

    packet_hash: str
    replies: tuple[SeatReply, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "packet_hash": self.packet_hash,
            "replies": [r.as_dict() for r in self.replies],
            # Stated, not left to be counted. Three sittings ran at two
            # seats without that ever being visible in the output.
            "census": self.census,
        }

    @property
    def seats_present(self) -> tuple[str, ...]:
        return tuple(r.seat for r in self.replies if r.status == "replied")

    @property
    def seats_failed(self) -> tuple[str, ...]:
        """Seats that ran and failed — a different fact from absent."""
        return tuple(r.seat for r in self.replies if r.status == "failed")

    @property
    def census(self) -> dict[str, Any]:
        """How many of the expected seats actually spoke, and who did not.

        ``short_handed`` is the loud bit: a sitting below full strength
        is a degraded cross-model check, and the chair should read that
        from the record rather than infer it from a missing name.
        """
        present = self.seats_present
        return {
            "expected": len(self.replies),
            "replied": len(present),
            "short_handed": len(present) < len(self.replies),
            "not_replied": {
                r.seat: {"status": r.status, "reason": r.raw[:REASON_CHARS].strip()}
                for r in self.replies
                if r.status != "replied"
            },
        }

    def amendments_for(self, item_id: str) -> tuple[SeatAmendment, ...]:
        """Every seat amendment naming ``item_id``."""
        return tuple(a for r in self.replies for a in r.amendments if a.item_id == item_id)

    def proposed_dispositions(self, item_id: str) -> set[str]:
        """The distinct dispositions seats proposed for one item."""
        return {a.disposition for a in self.amendments_for(item_id)}


def build_sitting_brief(packet: Packet) -> str:
    """The brief. Its constraints ARE the D3 role limits, stated to the seat."""
    lines = [
        "You are one seat at a release-audit sitting. ONE round, no rebuttal.",
        "",
        "You are NOT reviewing a diff and you are NOT looking for defects.",
        "That role was measured and ruled out. Do not ask for the diff.",
        "",
        "You have exactly two jobs:",
        "  (a) For each residual item below, either accept its pre-filled",
        "      disposition or AMEND it. Amend BY ITEM ID.",
        "  (c) Rank which classes most need a gate before this release.",
        "",
        f"Dispositions are exactly: {', '.join(DISPOSITIONS)}.",
        "",
        "Reply in EXACTLY this format, nothing else:",
        "  AMEND <item_id> -> <DISPOSITION>: <one line why>",
        "  (repeat per amended item; write NO AMENDMENTS if you accept all)",
        "  GATE-RANK: <class_id>, <class_id>, ...",
        "  CLOSING: <one paragraph maximum>",
        "",
        "--- PACKET ---",
        f"range: {packet.sections.get('0_header', {}).get('tag_range', '?')}",
        f"swept: {packet.sections.get('0_header', {}).get('files_swept', '?')} of "
        f"{packet.sections.get('0_header', {}).get('files_changed', '?')} changed files",
        "",
        "RESIDUAL ITEMS (id | class | locus | pre-filled disposition):",
    ]
    if not packet.items:
        lines.append("  (none — an empty residual still sits)")
    for item in packet.items:
        lines.append(
            f"  {item.item_id} | {item.class_id} | {item.locus} | {item.default_disposition}"
        )
    exposure = packet.sections.get("3_ungated_exposure", [])
    if exposure:
        lines += ["", "UNGATED CLASSES over the changed surface (for GATE-RANK):"]
        lines += [f"  {row.get('class_id')}" for row in exposure]
    return "\n".join(lines)


def parse_seat_reply(seat: str, exit_code: int, text: str) -> SeatReply:
    """Parse one seat's reply. Never fabricates content on its behalf.

    Non-zero exits split two ways, because they are different facts: 127
    means the seat was never reachable (``absent``), anything else means
    it RAN and FAILED (``failed``) and its output carries the diagnosis.
    Both keep that output as ``raw``, which ``as_dict`` emits as
    ``reason`` — see the module docstring and issue #2311.
    """
    body = (text or "").strip()
    if exit_code == _EXIT_NOT_FOUND:
        return SeatReply(seat=seat, status="absent", raw=body)
    if exit_code != 0:
        return SeatReply(seat=seat, status="failed", raw=body)
    if not body:
        return SeatReply(seat=seat, status="absent", raw="exited 0 with no output")

    amendments = tuple(
        SeatAmendment(
            item_id=m.group("item"),
            disposition=m.group("disp").strip(),
            reason=m.group("reason").strip(),
        )
        for m in _AMEND.finditer(body)
    )
    ranking_match = _RANK.search(body)
    ranking = ()
    if ranking_match:
        ranking = tuple(
            part.strip() for part in ranking_match.group("ranking").split(",") if part.strip()
        )
    closing_match = _CLOSING.search(body)
    closing = closing_match.group("text").strip() if closing_match else ""

    # A reply that neither amends, nor says NO AMENDMENTS, nor ranks has
    # not answered the brief — recorded as-is rather than read as assent.
    answered = bool(amendments) or bool(_NO_AMENDMENTS.search(body)) or bool(ranking)
    if not answered:
        return SeatReply(seat=seat, status="format_noncompliant", closing=closing, raw=body)

    bad = [a for a in amendments if a.disposition not in DISPOSITIONS]
    if bad:
        return SeatReply(seat=seat, status="format_noncompliant", closing=closing, raw=body)

    return SeatReply(
        seat=seat,
        status="replied",
        amendments=amendments,
        gate_ranking=ranking,
        closing=closing,
        raw=body,
    )


def hold_sitting(
    packet: Packet,
    *,
    invoke: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    seats: tuple[str, ...] = SEATS,
) -> Sitting:
    """Run one round over ``packet`` and collect the replies.

    Args:
        packet: The residual packet the seats rule on.
        invoke: ``(recipe, brief) -> (exit_code, text)``. Defaults to the
            round table's seat runner. Injected so the sitting is testable
            without spending a single model call.
        seats: Seat names, in stable order.

    Returns:
        A :class:`Sitting`. A seat that was unreachable is ``absent``, a
        seat that ran and failed is ``failed``, and both carry the
        reason — neither is ever read as agreement.

    """
    from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

    recipes = dict(SEAT_RECIPES)
    runner = invoke or (
        lambda recipe, brief: default_invoke_seat(recipe, brief, reply_chars=SEAT_REPLY_CHARS)
    )
    brief = build_sitting_brief(packet)

    replies: list[SeatReply] = []
    for seat in seats:
        recipe = recipes.get(seat)
        if recipe is None:
            replies.append(SeatReply(seat=seat, status="absent", raw="no recipe"))
            continue
        try:
            exit_code, text = runner(recipe, brief)
        except (OSError, ValueError) as exc:  # a seat CLI that is not installed
            replies.append(SeatReply(seat=seat, status="failed", raw=str(exc)))
            continue
        replies.append(parse_seat_reply(seat, exit_code, text))

    return Sitting(packet_hash=packet.packet_hash, replies=tuple(replies))


def compute_sitting_delta(
    packet: Packet,
    rulings: dict[str, str],
    sitting: Sitting | None = None,
) -> dict[str, bool]:
    """D9 — per item, did the SITTING move the chair off the §7 default?

    True only when the final ruling differs from the pre-filled default
    AND some seat proposed that ruling. A chair who moves an item with no
    seat suggesting it did so on their own; crediting the sitting for
    that would inflate the very tally that decides whether the sitting
    keeps earning its place (D2/D9).
    """
    defaults = {item.item_id: item.default_disposition for item in packet.items}
    delta: dict[str, bool] = {}
    for item_id, default in defaults.items():
        final = rulings.get(item_id)
        moved = final is not None and final != default
        seat_backed = bool(sitting and final in sitting.proposed_dispositions(item_id))
        delta[item_id] = bool(moved and seat_backed)
    return delta
