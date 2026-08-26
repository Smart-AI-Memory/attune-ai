"""The sitting (release-audit-stage R3 step 4).

Two properties carry the design and both are about NOT inventing things:
an absent or malformed seat is never read as agreement, and the D9
delta credits the sitting only for changes a seat actually proposed.

No model calls: the seat runner is injected.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.classes.packet import Packet, ResidualItem
from attune.classes.sitting import (
    SEATS,
    Sitting,
    build_sitting_brief,
    compute_sitting_delta,
    hold_sitting,
    parse_seat_reply,
)


def _item(n: int, default: str = "GATE-FIRST") -> ResidualItem:
    return ResidualItem(
        item_id=f"hit:R7b:src/mod.py:{n}",
        kind="hit",
        class_id="C3",
        locus=f"src/mod.py:{n}",
        detail="parsed then used unguarded",
        default_disposition=default,
    )


def _packet(count: int = 2, **sections) -> Packet:
    base = {"0_header": {"tag_range": "v1..v2", "files_swept": 3, "files_changed": 9}}
    base.update(sections)
    return Packet(sections=base, items=tuple(_item(i) for i in range(count)))


def _reply(text: str, code: int = 0):
    return lambda recipe, brief: (code, text)


class TestBriefEncodesTheRoleLimits:
    """D3: seats advise and rank; they do NOT hunt defects."""

    def test_brief_forbids_defect_hunting(self):
        brief = build_sitting_brief(_packet())

        assert "NOT reviewing a diff" in brief
        assert "Do not ask for the diff" in brief

    def test_brief_lists_items_with_their_prefilled_defaults(self):
        packet = _packet(2)

        brief = build_sitting_brief(packet)

        for item in packet.items:
            assert item.item_id in brief
            assert item.default_disposition in brief

    def test_empty_residual_still_produces_a_brief(self):
        """D2 — the table sits every release, empty or not."""
        brief = build_sitting_brief(_packet(0))

        assert "empty residual still sits" in brief

    def test_ungated_classes_are_offered_for_gate_rank(self):
        packet = _packet(1, **{"3_ungated_exposure": [{"class_id": "H1"}, {"class_id": "G2"}]})

        brief = build_sitting_brief(packet)

        assert "GATE-RANK" in brief
        assert "H1" in brief and "G2" in brief


class TestAbsenceIsNeverAgreement:
    def test_nonzero_exit_is_failed_not_absent(self):
        """It RAN and failed — a different fact from never reachable."""
        reply = parse_seat_reply("codex", 1, "boom")

        assert reply.status == "failed"
        assert reply.amendments == ()
        assert reply.raw == "boom", "the diagnosis is kept, not discarded"

    def test_binary_not_found_is_absent(self):
        """127 is the one exit that means nothing ever spawned."""
        reply = parse_seat_reply("codex", 127, "codex: not found")

        assert reply.status == "absent"
        assert reply.amendments == ()

    def test_empty_output_is_absent(self):
        assert parse_seat_reply("codex", 0, "   ").status == "absent"

    def test_unparseable_reply_is_flagged_not_assumed(self):
        reply = parse_seat_reply("claude", 0, "Looks fine to me, ship it!")

        assert reply.status == "format_noncompliant"
        assert reply.amendments == ()
        assert reply.raw, "the raw text is preserved for the chair"

    def test_invalid_disposition_is_noncompliant(self):
        reply = parse_seat_reply("codex", 0, "AMEND hit:x -> LGTM: seems ok")

        assert reply.status == "format_noncompliant"

    def test_a_seat_runner_that_raises_is_not_fatal(self):
        def explode(recipe, brief):
            raise OSError("codex: command not found")

        sitting = hold_sitting(_packet(1), invoke=explode)

        assert {r.status for r in sitting.replies} == {"failed"}
        assert sitting.seats_present == ()

    def test_a_seat_that_did_not_reply_says_why(self):
        """Issue #2311: three sittings recorded a bare 'absent' while the
        CLI's own one-line diagnosis sat in raw and was never emitted.
        """
        auth_error = "Failed to authenticate: OAuth session expired and could not be refreshed"

        emitted = parse_seat_reply("claude", 1, auth_error).as_dict()

        assert emitted["status"] == "failed"
        assert auth_error in emitted["reason"]

    def test_a_replying_seat_carries_no_reason_field(self):
        emitted = parse_seat_reply(
            "codex", 0, "NO AMENDMENTS\nGATE-RANK: C4b\nCLOSING: fine"
        ).as_dict()

        assert emitted["status"] == "replied"
        assert "reason" not in emitted

    def test_census_states_short_handedness_rather_than_implying_it(self):
        """A two-seat sitting must SAY it was short-handed."""

        def only_codex_answers(recipe, brief):
            if recipe[0] == "codex":
                return 0, "NO AMENDMENTS\nGATE-RANK: C4b\nCLOSING: ok"
            return 1, "Failed to authenticate: OAuth session expired"

        census = hold_sitting(_packet(1), invoke=only_codex_answers).as_dict()["census"]

        assert census["replied"] == 1
        assert census["expected"] == 3
        assert census["short_handed"] is True
        assert set(census["not_replied"]) == {"claude", "antigravity"}
        assert "authenticate" in census["not_replied"]["claude"]["reason"].lower()


class TestParsingAReply:
    def test_amendments_and_ranking_and_closing(self):
        text = (
            "AMEND hit:R7b:src/mod.py:0 -> SHIP: fixture input, not external\n"
            "AMEND hit:R7b:src/mod.py:1 -> DEFER: gate lands next release\n"
            "GATE-RANK: H1, G2, C3\n"
            "CLOSING: Nothing here blocks the release.\n"
        )

        reply = parse_seat_reply("codex", 0, text)

        assert reply.status == "replied"
        assert [a.disposition for a in reply.amendments] == ["SHIP", "DEFER"]
        assert reply.gate_ranking == ("H1", "G2", "C3")
        assert "blocks the release" in reply.closing

    def test_no_amendments_is_a_valid_answer(self):
        reply = parse_seat_reply("claude", 0, "NO AMENDMENTS\nGATE-RANK: H1\n")

        assert reply.status == "replied"
        assert reply.amendments == ()

    def test_ranking_alone_counts_as_answering(self):
        assert parse_seat_reply("claude", 0, "GATE-RANK: H1, G2").status == "replied"


class TestHoldSitting:
    def test_runs_every_seat_once_no_rebuttal(self):
        calls = []

        def spy(recipe, brief):
            calls.append(recipe[0])
            return 0, "NO AMENDMENTS\nGATE-RANK: H1\n"

        sitting = hold_sitting(_packet(1), invoke=spy)

        assert len(calls) == len(SEATS), "one round, one call per seat"
        assert len(sitting.replies) == len(SEATS)

    def test_binds_to_the_packet_it_sat_on(self):
        packet = _packet(1)

        sitting = hold_sitting(packet, invoke=_reply("NO AMENDMENTS"))

        assert sitting.packet_hash == packet.packet_hash

    def test_collects_amendments_across_seats(self):
        packet = _packet(1)
        text = f"AMEND {packet.items[0].item_id} -> SHIP: controlled input\n"

        sitting = hold_sitting(packet, invoke=_reply(text))

        assert len(sitting.amendments_for(packet.items[0].item_id)) == len(SEATS)
        assert sitting.proposed_dispositions(packet.items[0].item_id) == {"SHIP"}


class TestD9DeltaCreditsOnlyTheSitting:
    """The tally decides whether the sitting keeps earning its place."""

    def test_change_a_seat_proposed_counts(self):
        packet = _packet(1)
        item = packet.items[0].item_id
        sitting = hold_sitting(packet, invoke=_reply(f"AMEND {item} -> SHIP: fixture\n"))

        delta = compute_sitting_delta(packet, {item: "SHIP"}, sitting)

        assert delta[item] is True

    def test_chair_moving_it_alone_does_NOT_count(self):
        """Crediting the sitting for a solo chair move would inflate D9."""
        packet = _packet(1)
        item = packet.items[0].item_id
        sitting = hold_sitting(packet, invoke=_reply("NO AMENDMENTS\nGATE-RANK: H1\n"))

        delta = compute_sitting_delta(packet, {item: "SHIP"}, sitting)

        assert delta[item] is False

    def test_accepting_the_default_is_not_a_delta(self):
        packet = _packet(1)
        item = packet.items[0].item_id
        sitting = hold_sitting(packet, invoke=_reply("NO AMENDMENTS\n"))

        delta = compute_sitting_delta(packet, {item: "GATE-FIRST"}, sitting)

        assert delta[item] is False

    def test_delta_covers_every_item_so_the_manifest_validates(self):
        packet = _packet(3)
        rulings = {i.item_id: i.default_disposition for i in packet.items}

        delta = compute_sitting_delta(packet, rulings, None)

        assert set(delta) == {i.item_id for i in packet.items}
        assert not any(delta.values())


class TestSittingShape:
    def test_serialises_for_the_record(self):
        packet = _packet(1)
        sitting = hold_sitting(packet, invoke=_reply("NO AMENDMENTS\nGATE-RANK: H1\n"))

        data = sitting.as_dict()

        assert data["packet_hash"] == packet.packet_hash
        assert {r["seat"] for r in data["replies"]} == set(SEATS)

    def test_is_frozen(self):
        sitting = Sitting(packet_hash="h", replies=())

        with pytest.raises(AttributeError):
            sitting.packet_hash = "other"  # type: ignore[misc]
