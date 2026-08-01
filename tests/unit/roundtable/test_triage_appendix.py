"""Triage appendix (T4, headless) — contract tests.

Board and seats are stubs; distillation, demotion state, brief
composition, and the skip paths (kill switch, demoted, zero items)
run real. No network, no Redis, no LLM.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from attune.roundtable import triage_appendix as ta

RECIPES = (("claude", ("claude", "-p", "{brief}")),)


class StubBoard:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def post_message(self, thread, author, kind, body, **extra):
        self.messages.append(
            {"thread": thread, "author": author, "kind": kind, "body": body, **extra}
        )
        return len(self.messages)


def _ok_seat(recipe, brief):
    return 0, "ITEM 1: recommendation. RISK: none."


@pytest.fixture
def state(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


class TestDistill:
    def test_cap_at_five_names_dropped(self):
        items = [ta.TriageItem(f"t{i}", "e", "q") for i in range(8)]
        kept, dropped = ta.distill(items)
        assert len(kept) == 5
        assert dropped == 3

    def test_under_cap_drops_nothing(self):
        kept, dropped = ta.distill([ta.TriageItem("t", "e", "q")])
        assert len(kept) == 1
        assert dropped == 0


class TestComposeBrief:
    def test_brief_carries_items_dark_and_cap_note(self):
        items = [ta.TriageItem("title-one", "evidence-one", "q?")]
        brief = ta.compose_brief(items, ["sweep", "telemetry"], ["extra-line"], 2, "STAMP")
        assert "ITEM 1 — title-one" in brief
        assert "evidence-one" in brief
        assert "sweep, telemetry" in brief
        assert "extra-line" in brief
        assert "2 further candidate item(s) dropped" in brief
        assert "NOT to be re-litigated" in brief

    def test_no_cap_note_when_nothing_dropped(self):
        brief = ta.compose_brief([ta.TriageItem("t", "e", "q")], [], [], 0, "S")
        assert "dropped" not in brief


class TestDemotionState:
    def test_fresh_state_not_demoted(self, state):
        assert ta.is_demoted(state) is False

    def test_two_recorded_zero_ruling_digests_demote(self, state):
        ta.record_digest("t1", 3, path=state)
        ta.record_digest("t2", 2, path=state)
        ta.record_rulings("t1", 0, path=state)
        ta.record_rulings("t2", 0, path=state)
        assert ta.is_demoted(state) is True

    def test_unrecorded_outcomes_never_demote(self, state):
        ta.record_digest("t1", 3, path=state)
        ta.record_digest("t2", 2, path=state)
        assert ta.is_demoted(state) is False

    def test_nonzero_ruling_resets_the_streak(self, state):
        for thread, rulings in (("t1", 0), ("t2", 4)):
            ta.record_digest(thread, 1, path=state)
            ta.record_rulings(thread, rulings, path=state)
        assert ta.is_demoted(state) is False

    def test_record_rulings_unknown_thread_returns_false(self, state):
        ta.record_digest("t1", 1, path=state)
        assert ta.record_rulings("nope", 2, path=state) is False


class TestRunSkipPaths:
    def test_kill_switch_skips_everything(self, state, monkeypatch, capsys):
        monkeypatch.setenv(ta.KILL_SWITCH_ENV, "off")
        board = StubBoard()
        used = ta.run_triage_appendix(
            board, "t", Path("/nonexistent"), _ok_seat, RECIPES, state_path=state
        )
        assert used == 0
        assert board.messages == []
        assert "kill switch" in capsys.readouterr().out

    def test_demoted_skips_everything(self, state, capsys):
        for thread in ("t1", "t2"):
            ta.record_digest(thread, 1, path=state)
            ta.record_rulings(thread, 0, path=state)
        board = StubBoard()
        used = ta.run_triage_appendix(
            board, "t", Path("/nonexistent"), _ok_seat, RECIPES, state_path=state
        )
        assert used == 0
        assert board.messages == []
        assert "DEMOTED" in capsys.readouterr().out

    def test_zero_items_posts_note_no_seats(self, state, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(ta, "pull_briefing", lambda root: ([], ["sweep"], []))
        board = StubBoard()
        used = ta.run_triage_appendix(board, "t", tmp_path, _ok_seat, RECIPES, state_path=state)
        assert used == 0
        assert len(board.messages) == 1
        assert board.messages[0]["kind"] == "appendix"
        assert "0 decidable items" in board.messages[0]["body"]
        assert "no spend" in capsys.readouterr().out
        # The zero-item digest still records (it feeds T4 demotion).
        digests = ta._load_state(state)["digests"]
        assert len(digests) == 1 and digests[0]["items"] == 0


class TestRunWithItems:
    def _items(self):
        return [ta.TriageItem("drifted-spec", "bucket approved-not-shipped", "disposition?")]

    def test_full_flow_posts_question_position_synthesis(self, state, tmp_path, monkeypatch):
        monkeypatch.setattr(ta, "pull_briefing", lambda root: (self._items(), [], ["ev"]))
        board = StubBoard()
        used = ta.run_triage_appendix(board, "t", tmp_path, _ok_seat, RECIPES, state_path=state)
        kinds = [m["kind"] for m in board.messages]
        assert kinds == ["question", "position", "synthesis"]
        assert all(m.get("appendix") == "triage" for m in board.messages)
        assert used == 2  # one seat + synthesis
        digests = ta._load_state(state)["digests"]
        assert digests[-1]["items"] == 1 and digests[-1]["rulings"] is None

    def test_absent_seat_tolerated_no_synthesis(self, state, tmp_path, monkeypatch):
        monkeypatch.setattr(ta, "pull_briefing", lambda root: (self._items(), [], []))

        def absent(recipe, brief):
            return 127, "not found"

        board = StubBoard()
        used = ta.run_triage_appendix(board, "t", tmp_path, absent, RECIPES, state_path=state)
        kinds = [m["kind"] for m in board.messages]
        assert kinds == ["question", "position"]
        assert board.messages[1]["absent"] is True
        assert used == 1


class TestPullBriefing:
    def test_empty_project_renders_dark_not_items(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
        candidates, dark, extra = ta.pull_briefing(tmp_path)
        assert candidates == []
        assert set(dark) <= set(ta.DARK_RENDER_SOURCES)
        assert any("gate verdict ledger" in line for line in extra)
        assert any("local spend" in line for line in extra)


class TestCiGateVerdicts:
    """A4/TA-5 — CI verdict fetch: timestamped, injectable, never raises."""

    def test_success_path_counts_and_names_failures(self, tmp_path):
        def runner(argv, cwd):
            if "repo" in argv:
                return 0, "Smart-AI-Memory/attune-ai"
            return 0, (
                '{"runs": [{"name": "pre-commit", "conclusion": "success"},'
                ' {"name": "coverage", "conclusion": "failure"},'
                ' {"name": "label", "conclusion": "skipped"}]}'
            )

        (line,) = ta._ci_gate_verdicts(tmp_path, runner=runner)
        assert "3 checks" in line
        assert "1 failure" in line and "1 success" in line
        assert "FAILING: coverage" in line
        assert "fetched" in line

    def test_gh_missing_renders_timestamped_unavailable(self, tmp_path):
        def runner(argv, cwd):
            return 127, "gh not found"

        (line,) = ta._ci_gate_verdicts(tmp_path, runner=runner)
        assert "unavailable" in line and "checked" in line

    def test_unparseable_reply_renders_unavailable(self, tmp_path):
        def runner(argv, cwd):
            if "repo" in argv:
                return 0, "o/r"
            return 0, "not-json"

        (line,) = ta._ci_gate_verdicts(tmp_path, runner=runner)
        assert "unparseable" in line

    def test_pull_briefing_includes_ci_line(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.setattr(ta, "_ci_gate_verdicts", lambda root: ["CI gate verdicts: STUB"])
        _c, _d, extra = ta.pull_briefing(tmp_path)
        assert "CI gate verdicts: STUB" in extra


class TestEvidenceTiers:
    """TA-9 — receipt-vs-claim labels travel into the brief."""

    def test_default_kind_is_receipt_and_rendered(self):
        brief = ta.compose_brief([ta.TriageItem("t", "live read", "q?")], [], [], 0, "S")
        assert "evidence[receipt]: live read" in brief

    def test_claim_kind_rendered_and_instruction_present(self):
        item = ta.TriageItem("t", "narrated statement", "q?", evidence_kind="claim")
        brief = ta.compose_brief([item], [], [], 0, "S")
        assert "evidence[claim]: narrated statement" in brief
        assert "UNVERIFIED" in brief

    def test_pull_briefing_items_are_receipts(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))

        class _Item:
            title = "drift"
            detail = "bucket x"
            item_id = "spec-drift:x"
            metadata = {}

        class _Summary:
            items = [_Item()]

        real_import = ta.importlib.import_module

        def fake_import(name):
            if name.endswith(".spec_drift"):

                class _Mod:
                    @staticmethod
                    def read(*, project_root):
                        return _Summary()

                return _Mod
            return real_import(name)

        monkeypatch.setattr(ta.importlib, "import_module", fake_import)
        monkeypatch.setattr(ta, "_ci_gate_verdicts", lambda root: [])
        candidates, _dark, _extra = ta.pull_briefing(tmp_path)
        assert candidates and all(c.evidence_kind == "receipt" for c in candidates)


class TestDefaultStatePath:
    """The unpathed state API resolves under ATTUNE_HOME."""

    def test_default_path_round_trips_under_attune_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        ta.record_digest("t-default", 2)
        assert (tmp_path / "ops" / "triage_appendix.json").is_file()
        assert ta.record_rulings("t-default", 1) is True
        assert ta.is_demoted() is False


class TestStateTolerance:
    """Corrupt or foreign state degrades to empty — never raises."""

    def test_malformed_json_degrades_to_empty(self, state, caplog):
        state.write_text("{not json", encoding="utf-8")
        with caplog.at_level("WARNING", logger="attune.roundtable.triage_appendix"):
            assert ta._load_state(state) == {"digests": []}
        assert "unreadable state" in caplog.text

    def test_non_dict_json_degrades_to_empty(self, state):
        state.write_text('["a", "b"]', encoding="utf-8")
        assert ta._load_state(state) == {"digests": []}

    def test_record_rulings_non_list_digests_returns_false(self, state):
        state.write_text('{"digests": "nope"}', encoding="utf-8")
        assert ta.record_rulings("t1", 2, path=state) is False


class TestPullBriefingUnreadableSource:
    """A raising source reader becomes UNREADABLE evidence, not a crash."""

    def test_raising_source_reported_and_others_still_read(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        real_import = ta.importlib.import_module

        def fake_import(name):
            if name.endswith(".bulletin"):
                raise RuntimeError("reader exploded")
            return real_import(name)

        monkeypatch.setattr(ta.importlib, "import_module", fake_import)
        monkeypatch.setattr(ta, "_ci_gate_verdicts", lambda root: [])
        candidates, _dark, extra = ta.pull_briefing(tmp_path)
        assert any(
            line.startswith("source bulletin: UNREADABLE") and "reader exploded" in line
            for line in extra
        )
        # The routine survived and still appended the standing evidence lines.
        assert any("local spend" in line for line in extra)


class TestRunGh:
    """_run_gh: fixed argv, degrades to coded reasons, never raises."""

    def test_missing_binary_returns_127(self, tmp_path):
        code, reason = ta._run_gh(["attune-no-such-binary-xyz"], tmp_path)
        assert code == 127
        assert reason == "gh not found"

    def test_timeout_returns_124(self, tmp_path, monkeypatch):
        def raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

        monkeypatch.setattr(subprocess, "run", raise_timeout)
        code, reason = ta._run_gh(["gh", "api", "x"], tmp_path)
        assert code == 124
        assert reason == "gh timed out"

    def test_success_returns_stdout(self, tmp_path):
        code, out = ta._run_gh([sys.executable, "-c", "print('ok')"], tmp_path)
        assert code == 0
        assert out == "ok"

    def test_failure_returns_stderr(self, tmp_path):
        code, out = ta._run_gh(
            [sys.executable, "-c", "import sys; sys.stderr.write('bad'); sys.exit(3)"],
            tmp_path,
        )
        assert code == 3
        assert out == "bad"


class TestCiGateVerdictsApiFailure:
    def test_api_error_renders_timestamped_unavailable(self, tmp_path):
        def runner(argv, cwd):
            if "repo" in argv:
                return 0, "o/r"
            return 1, "api down"

        (line,) = ta._ci_gate_verdicts(tmp_path, runner=runner)
        assert "unavailable" in line
        assert "api down" in line
        assert "checked" in line


class TestGateLedgerEvidence:
    """Real ledger round trip under a tmp ATTUNE_HOME — no mocks."""

    def _receipt(self, state: str, gate_id: str = "G-test", decisions_ref=None):
        from attune.gates.lifecycle.protocol import GateReceipt

        return GateReceipt(
            gate_id=gate_id,
            phase="execution",
            target="spec-x",
            state=state,
            decisions_ref=decisions_ref,
        )

    def test_unresolved_chair_required_named(self, tmp_path, monkeypatch):
        from attune.gates.lifecycle import ledger

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        ledger.append(self._receipt("CHAIR_REQUIRED"))
        (line,) = ta._gate_ledger_evidence()
        assert "1 unresolved CHAIR_REQUIRED receipt(s)" in line
        assert "G-test:spec-x" in line

    def test_present_ledger_without_unresolved(self, tmp_path, monkeypatch):
        from attune.gates.lifecycle import ledger

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        ledger.append(self._receipt("PASS"))
        (line,) = ta._gate_ledger_evidence()
        assert line == "gate verdict ledger: present, no unresolved CHAIR_REQUIRED receipts"

    def test_no_ledger_file_renders_dark(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        (line,) = ta._gate_ledger_evidence()
        assert line.startswith("gate verdict ledger: dark")

    def test_raising_ledger_renders_unreadable(self, tmp_path, monkeypatch):
        from attune.gates.lifecycle import ledger

        def boom():
            raise OSError("disk gone")

        monkeypatch.setattr(ledger, "ledger_path", boom)
        (line,) = ta._gate_ledger_evidence()
        assert "UNREADABLE" in line
        assert "disk gone" in line


class TestUsageFreshness:
    def test_missing_usage_renders_dark(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        assert ta._usage_freshness_evidence() == "local spend: dark (no usage.jsonl)"

    def test_fresh_usage_reports_age(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        usage = tmp_path / "telemetry" / "usage.jsonl"
        usage.parent.mkdir(parents=True)
        usage.write_text("{}\n", encoding="utf-8")
        line = ta._usage_freshness_evidence()
        assert line == "local spend: usage.jsonl last write 0h ago"


class TestRunSubCapAndSynthesisFailure:
    def _items(self):
        return [ta.TriageItem("drifted-spec", "evidence", "disposition?")]

    def test_sub_cap_halts_before_fourth_seat(self, state, tmp_path, monkeypatch):
        monkeypatch.setattr(ta, "pull_briefing", lambda root: (self._items(), [], []))
        recipes = tuple((seat, ("cmd", seat)) for seat in ("a", "b", "c", "d"))
        board = StubBoard()
        used = ta.run_triage_appendix(board, "t", tmp_path, _ok_seat, recipes, state_path=state)
        kinds = [m["kind"] for m in board.messages]
        assert kinds == ["question", "position", "position", "position", "halt", "synthesis"]
        halt = board.messages[4]
        assert halt["body"] == "appendix invocation sub-cap before seat 'd'"
        assert used == ta.APPENDIX_MAX_INVOCATIONS

    def test_synthesis_failure_posts_halt(self, state, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(ta, "pull_briefing", lambda root: (self._items(), [], []))

        def seat_ok_synthesis_fails(recipe, brief):
            if brief.startswith("You are the moderator"):
                return 1, "synthesis exploded"
            return 0, "ITEM 1: recommendation."

        board = StubBoard()
        used = ta.run_triage_appendix(
            board, "t", tmp_path, seat_ok_synthesis_fails, RECIPES, state_path=state
        )
        kinds = [m["kind"] for m in board.messages]
        assert kinds == ["question", "position", "halt"]
        assert "appendix synthesis failed (exit 1)" in board.messages[2]["body"]
        assert "synthesis exploded" in board.messages[2]["body"]
        assert used == 2
        assert "synthesis: FAILED (exit 1)" in capsys.readouterr().out
        # The failed-synthesis run still records its digest (T4 input).
        digests = ta._load_state(state)["digests"]
        assert digests[-1]["items"] == 1
