"""Fix-loop tests (advanced-debugging-plugin T6) — mocked seats, REAL
materialize/validate/discard against a scratch git repo.
"""

import subprocess

import pytest

from attune.diagnosis.config import DiagnosisConfig
from attune.diagnosis.fix_loop import confidence_meets_threshold, run_fix_loop
from attune.models.telemetry.data_models import DiagnosisHypothesis, DiagnosisRecord

GOOD_PROPOSAL = "--- file: fixme.py\n```\nVALUE = 2\n```\n"
BROKEN_PROPOSAL = "--- file: fixme.py\n```\ndef broken(:\n```\n"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
    (root / "fixme.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True)
    return root


def _record(confidence="high"):
    return DiagnosisRecord(
        diagnosis_id="d1",
        source_run_id="r1",
        workflow_name="code-review",
        created_at="2026-07-20T12:00:00+00:00",
        symptom="VALUE wrong",
        hypotheses=[DiagnosisHypothesis(statement="[s] VALUE should be 2", confidence=confidence)],
        synthesis="VALUE should be 2",
    )


def _seats(proposer_reply, reviewer_reply):
    """proposer_reply: one (code, text) tuple, or a list of them in order."""
    queue = list(proposer_reply) if isinstance(proposer_reply, list) else [proposer_reply]
    calls = []

    def invoke(recipe, brief):
        calls.append((recipe[0], brief))
        if recipe[0] == "proposer":
            return queue.pop(0) if queue else (1, "")
        return reviewer_reply

    roster = (("proposer", ("proposer",)), ("reviewer", ("reviewer",)))
    return roster, invoke, calls


class TestThreshold:
    def test_low_confidence_gates_out_without_spend(self, repo):
        roster, invoke, calls = _seats((0, GOOD_PROPOSAL), (0, "VERDICT: APPROVE"))
        result = run_fix_loop(_record("low"), repo, seats=roster, invoke_seat=invoke)
        assert result["disposition"] == "below-threshold"
        assert calls == []  # no seat invoked, no spend

    def test_meets_threshold_by_scale_index(self):
        assert confidence_meets_threshold(_record("high"), DiagnosisConfig())
        assert not confidence_meets_threshold(_record("medium"), DiagnosisConfig())
        assert not confidence_meets_threshold(
            DiagnosisRecord(
                diagnosis_id="d",
                source_run_id="r",
                workflow_name="w",
                created_at="2026-07-20T12:00:00+00:00",
            ),
            DiagnosisConfig(),
        )  # no hypotheses -> never


class TestLoop:
    def test_happy_path_proposed_and_tree_untouched(self, repo):
        roster, invoke, calls = _seats((0, GOOD_PROPOSAL), (0, "VERDICT: APPROVE\nlooks right"))
        before = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
        ).stdout
        result = run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        after = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
        ).stdout
        assert result["disposition"] == "proposed"
        assert result["proposer"] == "proposer" and result["reviewer"] == "reviewer"
        assert result["checks"][0]["label"] == "py-compile"
        assert result["checks"][0]["exit_code"] == 0
        assert "VALUE = 2" in result["diff"]
        assert before == after == ""  # user repo never touched
        assert (repo / "fixme.py").read_text() == "VALUE = 1\n"
        # both seats spoke, reviewer differs from proposer
        assert [c[0] for c in calls] == ["proposer", "reviewer"]

    def test_failed_validation_stays_visible(self, repo):
        roster, invoke, calls = _seats((0, BROKEN_PROPOSAL), (0, "VERDICT: APPROVE"))
        result = run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        assert result["disposition"] == "failed-validation"
        assert result["checks"][0]["exit_code"] != 0
        assert result["checks"][0]["tail"]  # the receipt carries the failure
        assert [c[0] for c in calls] == ["proposer"]  # no review of a red candidate

    def test_repair_round_recovers_bad_format(self, repo):
        roster, invoke, calls = _seats(
            [(0, "here is my fix in prose only"), (0, GOOD_PROPOSAL)],
            (0, "VERDICT: APPROVE"),
        )
        result = run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        assert result["disposition"] == "proposed"
        assert result["repair_rounds"] == 1
        assert "failed" in calls[1][1]  # repair brief carries the error

    def test_reviewer_reject_is_rejected(self, repo):
        roster, invoke, _calls = _seats((0, GOOD_PROPOSAL), (0, "VERDICT: REJECT\nrisky"))
        result = run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        assert result["disposition"] == "rejected"
        assert "risky" in result["review"]

    def test_proposer_absent_is_explicit(self, repo):
        roster, invoke, _calls = _seats((1, "401 revoked"), (0, "VERDICT: APPROVE"))
        result = run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        assert result["disposition"] == "proposer-absent"

    def test_scratch_worktrees_discarded(self, repo, tmp_path):
        roster, invoke, _calls = _seats((0, GOOD_PROPOSAL), (0, "VERDICT: APPROVE"))
        run_fix_loop(_record(), repo, seats=roster, invoke_seat=invoke)
        leaked = subprocess.run(
            ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True
        ).stdout
        assert "rt-candidate-" not in leaked  # discard ran (finally)
