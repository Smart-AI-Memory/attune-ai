"""Producing-routine tests (V2-P4: RR-3, RR-5, RR-6, RR-7).

Seats are injected fakes — no member CLI is invoked. Board writes go
against a REAL Redis (the test_board.py pattern) so thread shape,
ledger CAS, and TTL-exemption are non-mocked receipts; tests skip
when Redis is unreachable. Every test uses a unique run id and
removes its ledger keys on the way out (the ledger is deliberately
TTL-exempt, so cleanup is on us).
"""

from __future__ import annotations

import sys
import uuid

import pytest

from attune.roundtable import compiler
from attune.roundtable.board import LEDGER_ORDER_KEY, Board
from attune.roundtable.producing import (
    CITATION_EXAMPLE,
    DEFAULT_MAX_INVOCATIONS,
    FAILURE_CODES,
    TAG_EXAMPLE,
    TR6_CAP,
    FailureReceipt,
    ProducingSpec,
    _critique_brief,
    _final_brief,
    _repair_brief,
    render_digest,
    run_producing,
)
from attune.roundtable.routine import run_command


def _real_board_or_skip() -> Board:
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("no reachable Redis on localhost:6379")
    board = Board(client=client)
    board.ensure_functions()
    return board


def _cleanup(board: Board, run_id: str) -> None:
    board.client.lrem(LEDGER_ORDER_KEY, 0, run_id)
    board.client.delete(Board.ledger_record_key(run_id))
    board.client.delete(Board.thread_key(run_id))
    board.client.delete(Board.thread_key(run_id) + ":meta")


DRAFT_OK = """## Requirements

**RR-1 — First thing**

Rationale one.

- acceptance one
- acceptance two

**RR-2 — Second thing**

Rationale two.

- acceptance one
- acceptance two

## Non-goals

- nothing else
"""

CRITIQUE_OK = """1. **RR-1:** acceptance criteria too loose; see PACK-1 and src/attune/roundtable/routine.py.

VERDICT: ready-with-edits
"""

FINAL_OK = """## Requirements

**RR-1 — First thing**
[tag: agreed]

Rationale one.

- acceptance one
- acceptance two

**RR-2 — Second thing**
[tag: 2-1 codex dissents on shape]

Rationale two.

- acceptance one
- acceptance two

## Non-goals

- nothing else

## Dissent register

1. codex objected to RR-2's shape; the drafter rejected the objection because the ruled contract already covers it end to end.
"""


def _final_with_items(count: int) -> str:
    blocks = []
    for n in range(1, count + 1):
        blocks.append(f"**RR-{n} — Thing {n}**\n[tag: agreed]\n\nRationale.\n\n- one\n- two\n")
    return (
        "## Requirements\n\n"
        + "\n".join(blocks)
        + "\n## Non-goals\n\n- nothing else\n\n## Dissent register\n\n"
        + "Empty — attested: all critique items absorbed.\n"
    )


class FakeSeats:
    """Scripted seat invoker: (seat, role, brief) -> (exit, reply)."""

    def __init__(
        self,
        draft: str = DRAFT_OK,
        final: str = FINAL_OK,
        critique: str = CRITIQUE_OK,
        absent: set[tuple[str, str]] | None = None,
        drafter_final_absent: bool = False,
        dirty_draft_repairs: bool = False,
    ) -> None:
        self.draft = draft
        self.final = final
        self.critique = critique
        self.absent = absent or set()
        self.drafter_final_absent = drafter_final_absent
        self.dirty_draft_repairs = dirty_draft_repairs
        self.calls: list[tuple[str, str]] = []

    def __call__(self, seat: str, role: str, brief: str) -> tuple[int, str]:
        self.calls.append((seat, role))
        if (seat, role) in self.absent:
            return 1, "CLI not found"
        if role == "critic":
            return 0, self.critique
        if brief.startswith("Your previous reply failed"):
            return (0, self.draft) if self.dirty_draft_repairs else (0, "still dirty")
        if brief.startswith("You are the DRAFTER seat. Revise"):
            return (1, "gone") if self.drafter_final_absent else (0, self.final)
        if self.dirty_draft_repairs:
            return 0, "no items here at all"
        return 0, self.draft


def _spec(tmp_path, **overrides) -> ProducingSpec:
    pack = tmp_path / "pack.md"
    pack.write_text("# Grounding pack\n\nPACK-1 — facts.\n")
    fields = {
        "slug": "t-" + uuid.uuid4().hex[:8],
        "subject": "Test Subject",
        "grounding_pack": str(pack),
        "slot": "s1",
    }
    fields.update(overrides)
    return ProducingSpec(**fields)


class TestHappyPath:
    def test_clean_run_stages_unruled_candidates(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats()
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "clean"
            assert result.invocations == 4  # draft + 2 critiques + final
            assert result.staged == ["RR-1", "RR-2"]
            kinds = [m.kind for m in board.read_thread(spec.run_id)]
            assert kinds.count("question") == 1
            assert kinds.count("event") == 1  # scheduled-assignment
            assert kinds.count("position") == 4  # draft, 2 critiques, final
            assert kinds.count("candidate") == 2
            assert kinds.count("synthesis") == 1
        finally:
            _cleanup(board, spec.run_id)

    def test_routine_never_promotes(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            run_producing(spec, board=board, invoke=FakeSeats())
            meta = board.client.hgetall(Board.thread_key(spec.run_id) + ":meta")
            assert meta.get("status") != "promoted"
            assert "destination" not in meta
        finally:
            _cleanup(board, spec.run_id)

    def test_ledger_records_served_drafter(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            run_producing(spec, board=board, invoke=FakeSeats())
            record = board.client.hgetall(Board.ledger_record_key(spec.run_id))
            assert record["owed_seat"] == "claude"
            assert record["actual_drafter"] == "claude"
            assert record["served"] == "1"
        finally:
            _cleanup(board, spec.run_id)

    def test_ledger_is_ttl_exempt(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            run_producing(spec, board=board, invoke=FakeSeats())
            assert board.client.ttl(LEDGER_ORDER_KEY) == -1
            assert board.client.ttl(Board.ledger_record_key(spec.run_id)) == -1
            # The deliberation thread itself still expires (AC-6).
            assert board.client.ttl(Board.thread_key(spec.run_id)) > 0
        finally:
            _cleanup(board, spec.run_id)

    def test_provenance_event_precedes_every_position(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            run_producing(spec, board=board, invoke=FakeSeats())
            messages = board.read_thread(spec.run_id)
            event_id = next(m.id for m in messages if m.kind == "event")
            first_position = next(m.id for m in messages if m.kind == "position")
            assert event_id < first_position
            events = board.read_events(spec.run_id)
            assert events[0].body == "scheduled-assignment"
            assert events[0].extra["basis"] == "fixed"
        finally:
            _cleanup(board, spec.run_id)


class TestLintGates:
    def test_dirty_draft_gets_one_repair_and_completes(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(dirty_draft_repairs=True)
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "clean"
            assert result.invocations == 5  # + one repair, intra-round
            assert "ROUND_CEILING" not in [r.code for r in result.receipts]
        finally:
            _cleanup(board, spec.run_id)

    def test_dirty_after_repair_terminates_with_zero_candidates(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats()
            seats.draft = "no requirement items here"
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "failed"
            assert [r.code for r in result.receipts] == ["LINT_DIRTY"]
            assert result.receipts[0].evidence  # literal lint output
            assert result.staged == []
            record = board.client.hgetall(Board.ledger_record_key(spec.run_id))
            assert record["served"] == "0"
        finally:
            _cleanup(board, spec.run_id)


class TestAbsence:
    def test_drafter_absent_at_open_substitutes_and_degrades(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(absent={("claude", "drafter")})
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "degraded"
            assert "SEAT_ABSENT" in [r.code for r in result.receipts]
            record = board.client.hgetall(Board.ledger_record_key(spec.run_id))
            assert record["owed_seat"] == "claude"
            assert record["actual_drafter"] == "antigravity"
            assert record["served"] == "1"
            events = board.read_events(spec.run_id)
            assert any(e.body == "fallback" for e in events)
        finally:
            _cleanup(board, spec.run_id)

    def test_drafter_lost_mid_round_is_typed_terminal(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(drafter_final_absent=True)
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "failed"
            assert result.receipts[-1].code == "SEAT_ABSENT"
            assert result.receipts[-1].round == 3
            assert result.staged == []
            # Completed rounds are preserved on the thread.
            kinds = [m.kind for m in board.read_thread(spec.run_id)]
            assert kinds.count("position") == 3  # draft + 2 critiques
            # The drafter SERVED round 1 — a later loss never unserves.
            record = board.client.hgetall(Board.ledger_record_key(spec.run_id))
            assert record["served"] == "1"
        finally:
            _cleanup(board, spec.run_id)

    def test_zero_critics_proceeds_flagged_uncritiqued(self, tmp_path) -> None:
        # Chair ruling 2026-07-19: R6 preserved; flag, don't abort.
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(absent={("antigravity", "critic"), ("codex", "critic")})
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "degraded"
            assert "UNCRITIQUED" in [r.code for r in result.receipts]
            candidates = [m for m in board.read_thread(spec.run_id) if m.kind == "candidate"]
            assert candidates and all(m.extra.get("uncritiqued") for m in candidates)
        finally:
            _cleanup(board, spec.run_id)


class TestStagingCap:
    def test_nine_items_stage_seven_defer_two(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(final=_final_with_items(9))
            result = run_producing(spec, board=board, invoke=seats)
            assert len(result.staged) == TR6_CAP
            assert result.deferred == ["RR-8", "RR-9"]
            assert result.status == "degraded"  # over-cap = degraded
            deferred = [
                m
                for m in board.read_thread(spec.run_id)
                if m.kind == "candidate" and m.extra.get("deferred_over_cap")
            ]
            assert len(deferred) == 2
            assert all(m.body for m in deferred)  # full text preserved
        finally:
            _cleanup(board, spec.run_id)


class TestInputAndBudget:
    def test_missing_pack_is_input_invalid_before_any_seat(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path, grounding_pack=str(tmp_path / "absent.md"))
        try:
            seats = FakeSeats()
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "failed"
            assert result.receipts[0].code == "INPUT_INVALID"
            assert seats.calls == []
            assert result.invocations == 0
        finally:
            _cleanup(board, spec.run_id)

    def test_empty_pack_is_input_invalid(self, tmp_path) -> None:
        board = _real_board_or_skip()
        empty = tmp_path / "empty.md"
        empty.write_text("  \n")
        spec = _spec(tmp_path, grounding_pack=str(empty))
        try:
            result = run_producing(spec, board=board, invoke=FakeSeats())
            assert [r.code for r in result.receipts] == ["INPUT_INVALID"]
        finally:
            _cleanup(board, spec.run_id)

    def test_failing_precheck_terminates_with_evidence(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path, checks=(("boom", ("false",)),))
        try:
            seats = FakeSeats()
            result = run_producing(spec, board=board, invoke=seats)
            assert result.receipts[0].code == "PRECHECK_FAILED"
            assert seats.calls == []
        finally:
            _cleanup(board, spec.run_id)

    def test_duplicate_run_makes_no_writes(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            run_producing(spec, board=board, invoke=FakeSeats())
            before = len(board.read_thread(spec.run_id))
            result = run_producing(spec, board=board, invoke=FakeSeats())
            assert result.status == "failed"
            assert result.thread is None
            assert result.receipts[0].code == "DUPLICATE_RUN"
            assert "evidence" not in result.receipts[0].to_dict()
            assert len(board.read_thread(spec.run_id)) == before
        finally:
            _cleanup(board, spec.run_id)

    def test_budget_exhaustion_posts_halt_and_preserves_rounds(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path, max_invocations=2)
        try:
            result = run_producing(spec, board=board, invoke=FakeSeats())
            assert result.status == "failed"
            assert result.receipts[-1].code == "BUDGET_EXHAUSTED"
            kinds = [m.kind for m in board.read_thread(spec.run_id)]
            assert "halt" in kinds
            assert kinds.count("position") >= 1  # round 1 preserved
        finally:
            _cleanup(board, spec.run_id)


class TestReceiptsAndDigest:
    def test_unknown_failure_code_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown failure code"):
            FailureReceipt(code="SOMETHING_NEW", run_id="r")

    def test_taxonomy_is_closed_at_twelve(self) -> None:
        assert len(FAILURE_CODES) == 12
        assert len(set(FAILURE_CODES)) == 12

    def test_evidence_is_capped_verbatim_tail(self) -> None:
        receipt = FailureReceipt(code="LINT_DIRTY", run_id="r", evidence="x" * 9000)
        assert len(receipt.evidence) == 2000

    def test_reserved_codes_are_constructible(self) -> None:
        for code in ("ROUND_CEILING", "MATERIALIZE_FAILED"):
            assert FailureReceipt(code=code, run_id="r").to_dict()["code"] == code

    def test_digest_puts_failures_before_candidates(self) -> None:

        receipt = FailureReceipt(code="SEAT_ABSENT", run_id="r", seat="codex")
        final = compiler.parse_draft(FINAL_OK)
        digest = render_digest("degraded", [receipt], final, ["RR-1", "RR-2"], [])
        assert digest.index("SEAT_ABSENT") < digest.index("Agreed candidates")
        assert digest.index("Dissent register") < digest.index("Agreed candidates")

    def test_clean_and_degraded_headers_differ(self) -> None:
        clean = render_digest("clean", [], None, ["RR-1"], [])
        degraded = render_digest(
            "degraded",
            [FailureReceipt(code="UNCRITIQUED", run_id="r")],
            None,
            ["RR-1"],
            [],
        )
        assert clean.splitlines()[0] != degraded.splitlines()[0]
        assert "conditions: none" in clean
        assert "UNCRITIQUED" in degraded

    def test_default_cap_is_the_chair_ratified_ten(self) -> None:
        assert DEFAULT_MAX_INVOCATIONS == 10


class TestRoleBudgets:
    def test_flat_cap_not_applied_when_budget_passed(self) -> None:
        # RR-5: drafter replies must not be cut at the routine's flat
        # 8,000-char cap when a role budget is passed through.
        code, reply = run_command(
            (sys.executable, "-c", "print('x' * 12000)"),
            provider_clean=True,
            reply_chars=40_000,
        )
        assert code == 0
        assert len(reply) == 12_000

    def test_default_cap_unchanged_for_routine_positions(self) -> None:
        code, reply = run_command(
            (sys.executable, "-c", "print('x' * 12000)"),
            provider_clean=True,
        )
        assert code == 0
        assert len(reply) == 8_000


class TestBriefContracts:
    """The convergence-tag contract is taught by worked example.

    Prose alone failed twice in live headless runs (see the
    roundtable-producing-team spec's decisions.md): the drafter
    shipped every item untagged, including after the repair round.
    A literal example block got the drafter through lint_final on
    the first attempt in the interactive loop (us-refresh-001).
    """

    def test_final_brief_embeds_worked_example(self) -> None:
        brief = _final_brief("subject", "the draft", {})
        assert TAG_EXAMPLE in brief
        assert "**RR-1 — Example requirement title**\n[tag: agreed]" in brief

    def test_worked_example_actually_carries_the_tag(self) -> None:
        # The taught shape must satisfy the parser it is teaching to.
        draft = compiler.parse_draft(TAG_EXAMPLE)
        assert [i.item_id for i in draft.items] == ["RR-1"]
        assert draft.items[0].tag == "agreed"

    def test_repair_brief_restates_example_on_tag_problems(self) -> None:
        problems = ["RR-2: missing convergence tag (agreed / 2-1 / contested)"]
        repair = _repair_brief("orig brief", "prev reply", problems)
        assert TAG_EXAMPLE in repair
        assert "ORIGINAL BRIEF:\n\norig brief" in repair

    def test_repair_brief_stays_compact_without_tag_problems(self) -> None:
        repair = _repair_brief("orig brief", "prev reply", ["no requirement items found"])
        assert TAG_EXAMPLE not in repair


class TestSymbolRealityGateOnFinal:
    """T5 of spec-lifecycle-gates: the post-compile boundary gate.

    A final draft citing unresolvable paths must degrade the run
    with a LINT_DIRTY gate receipt in the digest — candidates still
    stage for the chair (non-terminal, per the design's trigger #2;
    motivating episode: the slot-3 confabulated draft).
    """

    def test_confabulated_final_degrades_with_gate_receipt(self, tmp_path) -> None:
        board = _real_board_or_skip()
        confabulated_final = FINAL_OK.replace(
            "Rationale one.",
            "Rationale one, per `attune/nonexistent/thing.py`.",
        )
        spec = _spec(tmp_path)
        try:
            seats = FakeSeats(final=confabulated_final)
            result = run_producing(spec, board=board, invoke=seats)
            assert result.status == "degraded"
            gate_receipts = [
                r
                for r in result.receipts
                if r.code == "LINT_DIRTY" and "symbol-reality" in r.detail
            ]
            assert len(gate_receipts) == 1
            assert "attune/nonexistent/thing.py" in (gate_receipts[0].evidence or "")
            assert result.staged  # non-terminal: candidates still staged
        finally:
            _cleanup(board, spec.run_id)

    def test_clean_final_stays_clean(self, tmp_path) -> None:
        board = _real_board_or_skip()
        spec = _spec(tmp_path)
        try:
            result = run_producing(spec, board=board, invoke=FakeSeats())
            assert result.status == "clean"  # gate PASS adds no receipt
        finally:
            _cleanup(board, spec.run_id)


class TestCritiqueCitationContract:
    """The citation contract is taught by worked example too.

    Prose alone failed live: the first spec-lifecycle-gates producing
    run (slot 20260719-1) went LINT_DIRTY on an uncited codex critique
    item that survived its repair round — the same heterogeneous-seat
    format-contract class TAG_EXAMPLE closed for round 3 (#1470).
    """

    def test_critique_brief_embeds_worked_example(self) -> None:
        brief = _critique_brief("subject", "the pack", "the draft")
        assert CITATION_EXAMPLE in brief

    def test_worked_example_actually_passes_the_citation_lint(self) -> None:
        # The taught shape must satisfy the lint it is teaching to —
        # wrap it exactly as a critique reply would arrive.
        reply = CITATION_EXAMPLE.split(":\n", 1)[1] + "\nVERDICT: ready-with-edits"
        assert compiler.lint_critique(reply) == []

    def test_repair_brief_restates_example_on_uncited_problems(self) -> None:
        problems = ["uncited critique item (no pack/file reference): '12. **RR-7:**'"]
        repair = _repair_brief("orig brief", "prev reply", problems)
        assert CITATION_EXAMPLE in repair

    def test_repair_brief_stays_compact_without_citation_problems(self) -> None:
        repair = _repair_brief("orig brief", "prev reply", ["no requirement items found"])
        assert CITATION_EXAMPLE not in repair
