"""Triage appendix (T4, headless) — contract tests.

Board and seats are stubs; distillation, demotion state, brief
composition, and the skip paths (kill switch, demoted, zero items)
run real. No network, no Redis, no LLM.
"""

from __future__ import annotations

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
