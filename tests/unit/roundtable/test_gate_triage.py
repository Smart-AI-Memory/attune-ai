"""Gate-triage inbox tests (round-table P2, issue #1587).

Real ledger/state/telemetry files in tmp — no mocked persistence
(the read-only ledger seam is the point). Seat invocations and the
board are injected fakes; the ruled governance (read-only ledger,
threshold gating, closed enum, dedup, RR-4 eligibility, dissent
routing, R8 never-promotes) is asserted from the pass record plus
posted messages.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime as dt
import json

import pytest

from attune.gates.lifecycle.ledger import append
from attune.gates.lifecycle.protocol import GateReceipt
from attune.roundtable import role_telemetry
from attune.roundtable.gate_triage import (
    NO_RECOMMENDATION,
    THRESHOLD_PENDING,
    TRIAGE_DISPOSITIONS,
    build_table_brief,
    collect_shortfalls,
    load_triaged,
    parse_dispositions,
    past_threshold,
    run_triage,
)
from attune.roundtable.rotation import CANONICAL_SEATS


class FakeBoard:
    def __init__(self):
        self.posts = []

    def post_message(self, thread, seat, kind, body, **fields):
        self.posts.append({"thread": thread, "seat": seat, "kind": kind, "body": body, **fields})
        return len(self.posts)


RECIPES = tuple((seat, (f"seat-{seat}",)) for seat in CANONICAL_SEATS)


def invoker(replies):
    def invoke(recipe, brief):
        seat = recipe[0].removeprefix("seat-")
        return replies.get(seat, (1, ""))

    return invoke


def receipt(target="demo-spec", gate="symbol-reality", state="CHAIR_REQUIRED", **kw):
    return GateReceipt(gate_id=gate, phase="tasks", target=target, state=state, **kw)


@pytest.fixture
def paths(tmp_path):
    return {
        "ledger_path": tmp_path / "verdicts.jsonl",
        "triage_state_path": tmp_path / "triage_state.json",
        "telemetry_path": tmp_path / "role_telemetry.jsonl",
    }


def seed(paths, *receipts):
    for r in receipts:
        append(r, path=paths["ledger_path"])


def reply_for(*groups, disposition="uphold"):
    return "\n".join(
        f"DISPOSITION: {t} :: {g} :: {disposition}\nREASON: grounded in findings"
        for (t, g) in groups
    )


class TestCollectShortfalls:
    def test_groups_by_target_and_gate(self, paths):
        seed(
            paths,
            receipt(findings=["a"]),
            receipt(findings=["b"]),
            receipt(target="other-spec", gate="falsifiability"),
        )
        shortfalls, ineligible = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        keys = [(s.target, s.gate_id) for s in shortfalls]
        assert keys == [("demo-spec", "symbol-reality"), ("other-spec", "falsifiability")]
        assert len(shortfalls[0].receipts) == 2
        assert ineligible == []

    def test_non_chair_required_excluded(self, paths):
        seed(paths, receipt(state="PASS"), receipt(state="BLOCKED"))
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        assert shortfalls == []

    def test_rr4_unknown_gate_named_not_dropped(self, paths):
        seed(paths, receipt(gate="invented-gate"))
        shortfalls, ineligible = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        assert shortfalls == []
        assert [r.gate_id for r in ineligible] == ["invented-gate"]

    def test_triaged_receipts_never_recollected(self, paths):
        r = receipt()
        seed(paths, r)
        paths["triage_state_path"].write_text(
            json.dumps({r.receipt_id: {"thread": "t", "at": "x", "disposition": "uphold"}})
        )
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        assert shortfalls == []


class TestThreshold:
    def _shortfalls(self, paths, *receipts):
        seed(paths, *receipts)
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        return shortfalls

    def test_below_both_arms_is_quiet(self, paths):
        shortfalls = self._shortfalls(paths, receipt(), receipt(target="b"))
        assert past_threshold(shortfalls) is False

    def test_count_arm(self, paths):
        rs = [receipt(target=f"s{i}") for i in range(THRESHOLD_PENDING)]
        assert past_threshold(self._shortfalls(paths, *rs)) is True

    def test_age_arm(self, paths):
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=49)).isoformat()
        shortfalls = self._shortfalls(paths, receipt(timestamp=old))
        assert past_threshold(shortfalls) is True

    def test_empty_is_never_past(self, paths):
        assert past_threshold([]) is False


class TestParseDispositions:
    def test_one_per_group_from_closed_enum(self, paths):
        seed(paths, receipt(), receipt(target="other-spec", gate="falsifiability"))
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        text = reply_for(("demo-spec", "symbol-reality"), disposition="waive")
        parsed = parse_dispositions(text, shortfalls)
        assert parsed[("demo-spec", "symbol-reality")] == "waive"
        assert parsed[("other-spec", "falsifiability")] == NO_RECOMMENDATION

    def test_out_of_enum_grade_is_no_recommendation(self, paths):
        seed(paths, receipt())
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        text = "DISPOSITION: demo-spec :: symbol-reality :: rubber-stamp\nREASON: x"
        parsed = parse_dispositions(text, shortfalls)
        assert parsed[("demo-spec", "symbol-reality")] == NO_RECOMMENDATION

    def test_enum_is_closed(self):
        assert NO_RECOMMENDATION not in TRIAGE_DISPOSITIONS


class TestRunTriage:
    def _run(self, paths, replies=None, dissents=(), receipts=None, board=None):
        if receipts is None:
            receipts = [receipt(target=f"s{i}", findings=[f"finding-{i}"]) for i in range(3)]
        seed(paths, *receipts)
        board = board if board is not None else FakeBoard()
        record = run_triage(
            board=board,
            invoke_seat=invoker(replies or {}),
            seat_recipes=RECIPES,
            dissents=dissents,
            thread="t-triage",
            now=dt.datetime.now(dt.timezone.utc),
            **paths,
        )
        return record, board

    def test_below_threshold_no_board_writes_no_spend(self, paths):
        record, board = self._run(paths, receipts=[receipt()])
        assert record.outcome == "below-threshold"
        assert record.invocations == 0
        assert board.posts == []

    def test_deliberated_path_marks_triaged_and_digests(self, paths):
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        record, board = self._run(paths, replies={"claude": (0, reply)})
        assert record.outcome == "deliberated"
        assert record.seat == "claude"
        assert all(d == "uphold" for d in record.dispositions.values())
        kinds = [p["kind"] for p in board.posts]
        assert kinds == ["question", "position", "synthesis"]
        triaged = load_triaged(path=paths["triage_state_path"])
        assert len(triaged) == 3
        assert all(v["disposition"] == "uphold" for v in triaged.values())

    def test_second_pass_is_quiet_dedup(self, paths):
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        self._run(paths, replies={"claude": (0, reply)})
        record2 = run_triage(
            board=FakeBoard(),
            invoke_seat=invoker({"claude": (0, reply)}),
            seat_recipes=RECIPES,
            thread="t-2",
            **paths,
        )
        assert record2.outcome == "below-threshold"
        assert record2.shortfalls == []

    def test_malformed_reply_records_no_recommendation(self, paths):
        record, _ = self._run(paths, replies={"claude": (0, "LGTM, ship it all")})
        assert record.outcome == "deliberated"
        assert set(record.dispositions.values()) == {NO_RECOMMENDATION}
        triaged = load_triaged(path=paths["triage_state_path"])
        assert all(v["disposition"] == NO_RECOMMENDATION for v in triaged.values())

    def test_absent_fallback_then_reply(self, paths):
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        record, board = self._run(paths, replies={"claude": (1, ""), "antigravity": (0, reply)})
        assert record.seat == "antigravity"
        assert record.invocations == 2
        assert len([p for p in board.posts if p.get("absent")]) == 1

    def test_all_absent_stays_pending_not_triaged(self, paths):
        record, board = self._run(paths, replies={})
        assert record.outcome == "table-absent"
        assert load_triaged(path=paths["triage_state_path"]) == {}
        assert any(p["kind"] == "halt" for p in board.posts)

    def test_never_alters_gate_state(self, paths):
        receipts = [receipt(target=f"s{i}") for i in range(3)]
        seed(paths, *receipts)
        before = paths["ledger_path"].read_bytes()
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        run_triage(
            board=FakeBoard(),
            invoke_seat=invoker({"claude": (0, reply)}),
            seat_recipes=RECIPES,
            thread="t-ro",
            **paths,
        )
        assert paths["ledger_path"].read_bytes() == before

    def test_skeptic_dissents_route_into_digest(self, paths):
        dissent = {"spec": "some-spec", "cite": "smoke :: pytest -q", "reason": "tail shows fail"}
        record, board = self._run(
            paths,
            replies={"claude": (0, reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)]))},
            dissents=[dissent],
        )
        synthesis = [p for p in board.posts if p["kind"] == "synthesis"][0]["body"]
        assert "P3 skeptic DISSENT on 'some-spec'" in synthesis
        assert "smoke :: pytest -q" in synthesis

    def test_dissents_alone_digest_without_table(self, paths):
        dissent = {"spec": "s", "cite": "c", "reason": "r"}
        record, board = self._run(paths, receipts=[], dissents=[dissent])
        assert record.outcome == "digested"
        assert record.invocations == 0
        assert [p["kind"] for p in board.posts] == ["synthesis"]

    def test_ineligible_named_in_digest(self, paths):
        receipts = [receipt(target=f"s{i}") for i in range(3)]
        receipts.append(receipt(target="odd", gate="invented-gate"))
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        record, board = self._run(paths, replies={"claude": (0, reply)}, receipts=receipts)
        synthesis = [p for p in board.posts if p["kind"] == "synthesis"][0]["body"]
        assert "ineligible" in synthesis and "odd::invented-gate" in synthesis

    def test_never_promotes(self, paths):
        reply = reply_for(*[(f"s{i}", "symbol-reality") for i in range(3)])
        _, board = self._run(paths, replies={"claude": (0, reply)})
        assert all(p["kind"] != "ruling" for p in board.posts)
        synthesis = [p for p in board.posts if p["kind"] == "synthesis"][0]["body"]
        assert "never alters gate state" in synthesis


class TestBrief:
    def test_brief_carries_findings_and_enum(self, paths):
        seed(paths, receipt(findings=["symbol X missing"]))
        shortfalls, _ = collect_shortfalls(
            ledger_path=paths["ledger_path"], triage_state_path=paths["triage_state_path"]
        )
        brief = build_table_brief(shortfalls)
        assert "symbol X missing" in brief
        for d in TRIAGE_DISPOSITIONS:
            assert d in brief
        assert "inbox ceremony" in brief


class TestMain:
    def test_dry_run_prints_grouping_no_spend(self, tmp_path, monkeypatch, capsys):
        from attune.roundtable.gate_triage import main

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        append(receipt(findings=["x"]), path=tmp_path / "ops" / "gates" / "verdicts.jsonl")
        append(
            receipt(target="odd", gate="invented-gate"),
            path=tmp_path / "ops" / "gates" / "verdicts.jsonl",
        )
        code = main(["--dry-run"])
        out = capsys.readouterr().out
        assert code == 0
        assert "convene=False" in out
        assert "demo-spec :: symbol-reality" in out
        assert "ineligible: odd :: invented-gate" in out


class TestRoleTelemetry:
    def test_pass_records_seat_and_digest_events(self, paths):
        reply = "DISPOSITION: s0 :: symbol-reality :: defer\nREASON: needs context"
        seed(paths, *[receipt(target=f"s{i}") for i in range(3)])
        run_triage(
            board=FakeBoard(),
            invoke_seat=invoker({"claude": (0, reply)}),
            seat_recipes=RECIPES,
            thread="t-telemetry",
            **paths,
        )
        rows = [
            json.loads(line)
            for line in paths["telemetry_path"].read_text().splitlines()
            if line.strip()
        ]
        events = [(r["role"], r["event"]) for r in rows]
        assert ("triage-seat", "invoked") in events
        assert ("triage-seat", "replied") in events
        assert ("moderator", "digest-posted") in events

    def test_chair_latency_derives_from_ruling(self, paths):
        p = paths["telemetry_path"]
        role_telemetry.record("moderator", "moderator", "t-x", "digest-posted", path=p)
        role_telemetry.record_chair_ruling("t-x", path=p)
        latency = role_telemetry.chair_latency_seconds("t-x", path=p)
        assert latency is not None and latency >= 0

    def test_unruled_digest_has_no_latency(self, paths):
        p = paths["telemetry_path"]
        role_telemetry.record("moderator", "moderator", "t-y", "digest-posted", path=p)
        assert role_telemetry.chair_latency_seconds("t-y", path=p) is None

    def test_write_failure_never_raises(self, tmp_path):
        blocked = tmp_path / "file-not-dir" / "t.jsonl"
        blocked.parent.write_text("a file, not a directory")
        role_telemetry.record("r", "s", "t", "e", path=blocked)  # must not raise

    def test_default_paths_resolve_under_attune_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        assert role_telemetry.telemetry_path() == (
            tmp_path / "ops" / "roundtable" / "role_telemetry.jsonl"
        )
        role_telemetry.record("r", "s", "t-home", "digest-posted")
        assert role_telemetry.chair_latency_seconds("t-home") is None

    def test_missing_file_reads_empty(self, tmp_path):
        assert role_telemetry.chair_latency_seconds("t", path=tmp_path / "absent.jsonl") is None

    def test_malformed_lines_skipped(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text('not json\n\n{"thread": "t-z", "event": "digest-posted", "at": "junk"}\n')
        # malformed JSON and unparseable timestamps never raise
        assert role_telemetry.chair_latency_seconds("t-z", path=p) is None

    def test_other_threads_ignored(self, tmp_path):
        p = tmp_path / "t.jsonl"
        role_telemetry.record("moderator", "moderator", "t-a", "digest-posted", path=p)
        role_telemetry.record_chair_ruling("t-b", path=p)
        assert role_telemetry.chair_latency_seconds("t-a", path=p) is None
