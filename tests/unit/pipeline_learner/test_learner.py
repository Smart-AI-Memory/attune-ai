"""Pipeline-learner fixture tests — every RR-pinned assertion.

Spec: docs/specs/pipeline-learner/requirements.md (chair-ruled
2026-07-19, source amended to the canonical run stream). These tests
ARE the RR-2/RR-3/RR-6/RR-7 acceptance probes; live surfacing (RR-5)
stays gated on RR-1 readiness and has no tests here by design.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.pipeline_learner import (
    Candidate,
    LearnerReport,
    ScaffoldError,
    filter_candidates,
    learn,
    ledger_path,
    load_corpus,
    load_decisions,
    mine_pairs,
    rank,
    record_decision,
    scaffold_acceptance,
)
from attune.pipeline_learner.corpus import RunRecord

# All fixture timestamps are post-cutover (start-clean, D3).
BASE = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
PROJECT = "attune-ai"


def _rec(
    workflow: str, at: datetime, *, trigger: str | None = "manual", rid: str = ""
) -> RunRecord:
    return RunRecord(
        workflow=workflow,
        started_at=at,
        trigger=trigger,
        project=PROJECT,
        run_id=rid or f"{workflow}-{at.isoformat()}",
    )


def _line(workflow: str, at: str, *, project: str | None = PROJECT, rid: str | None = None) -> str:
    data = {"workflow_name": workflow, "started_at": at, "run_id": rid or f"{workflow}@{at}"}
    if project is not None:
        data["project"] = project
    return json.dumps(data)


def _seven_pair_corpus() -> list[RunRecord]:
    """7 A→B occurrences across 7 days + sub-threshold noise (RR-2)."""
    records: list[RunRecord] = []
    for day in range(7):
        at = BASE + timedelta(days=day)
        records.append(_rec("code-review", at))
        records.append(_rec("security-audit", at + timedelta(minutes=5)))
    # Noise: 2 C→D occurrences — below min-support, must be filtered.
    for day in range(2):
        at = BASE + timedelta(days=day, hours=4)
        records.append(_rec("doc-audit", at))
        records.append(_rec("perf-audit", at + timedelta(minutes=3)))
    return records


class TestLoadCorpus:
    """RR-2 record schema + RR-4 single-project eligibility."""

    def test_eligible_record_loads_and_naive_ts_normalizes(self, tmp_path):
        f = tmp_path / "runs.jsonl"
        f.write_text(_line("code-review", "2026-08-01T10:00:00") + "\n", encoding="utf-8")
        records, stats = load_corpus(PROJECT, [f])
        assert stats.eligible == 1
        assert records[0].started_at.tzinfo is not None  # normalized to UTC

    def test_drops_are_counted_not_silent(self, tmp_path):
        f = tmp_path / "runs.jsonl"
        lines = [
            "{not json",
            _line("code-review", "not-a-timestamp"),
            _line("code-review", "2026-01-01T10:00:00+00:00"),  # pre-cutover
            _line("stub-workflow", "2026-08-01T10:00:00+00:00"),  # fixture name
            _line("code-review", "2026-08-01T10:00:00+00:00", project=None),
            _line("code-review", "2026-08-01T11:00:00+00:00", project="other-repo"),
            _line("code-review", "2026-08-01T12:00:00+00:00", rid="dup"),
            _line("code-review", "2026-08-01T12:30:00+00:00", rid="dup"),
        ]
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records, stats = load_corpus(PROJECT, [f])
        assert stats.eligible == len(records) == 1
        assert stats.dropped_malformed == 2
        assert stats.dropped_pre_cutover == 1
        assert stats.dropped_fixture == 1
        assert stats.dropped_no_project == 1
        assert stats.dropped_other_project == 1
        assert stats.dropped_duplicate == 1


class TestMinePairs:
    """RR-2 pair semantics, pinned."""

    def test_seven_occurrence_pair_surfaces_noise_filtered(self):
        cands = filter_candidates(mine_pairs(_seven_pair_corpus()))
        assert len(cands) == 1
        (c,) = cands
        assert (c.a, c.b) == ("code-review", "security-audit")
        assert c.support == 7
        assert c.ratio == 1.0

    def test_off_by_window_excluded(self):
        records = [
            _rec("code-review", BASE),
            _rec("security-audit", BASE + timedelta(minutes=31)),  # > 30-min window
        ]
        assert mine_pairs(records) == []

    def test_self_sequence_excluded(self):
        records = [_rec("code-review", BASE), _rec("code-review", BASE + timedelta(minutes=5))]
        assert mine_pairs(records) == []

    def test_intervening_workflow_does_not_break_pair(self):
        records = [
            _rec("code-review", BASE),
            _rec("doc-audit", BASE + timedelta(minutes=2)),  # intervening
            _rec("security-audit", BASE + timedelta(minutes=10)),
        ]
        pairs = {(c.a, c.b) for c in mine_pairs(records)}
        assert ("code-review", "security-audit") in pairs

    def test_ratio_denominator_is_a_occurrences(self):
        # 3 A runs, only 1 followed by B → ratio 1/3.
        records = [
            _rec("code-review", BASE),
            _rec("security-audit", BASE + timedelta(minutes=5)),
            _rec("code-review", BASE + timedelta(days=1)),
            _rec("code-review", BASE + timedelta(days=2)),
        ]
        (c,) = [x for x in mine_pairs(records) if x.b == "security-audit"]
        assert c.a_occurrences == 3
        assert c.support == 1
        assert c.ratio == pytest.approx(1 / 3)


class TestRank:
    """RR-3 deterministic, manual-over-auto, recency-decayed ranking."""

    def _candidate(self, a: str, support: int, manual: int, last_at: datetime) -> Candidate:
        return Candidate(
            a=a,
            b="security-audit",
            support=support,
            a_occurrences=support,  # ratio 1.0
            manual_pairs=manual,
            last_pair_at=last_at,
        )

    def test_two_runs_produce_identical_ordering(self):
        cands = [
            self._candidate("code-review", 7, 7, NOW - timedelta(days=3)),
            self._candidate("doc-audit", 5, 2, NOW - timedelta(days=1)),
            self._candidate("perf-audit", 5, 2, NOW - timedelta(days=1)),
        ]
        first = [(c.a, c.score) for c in rank(list(cands), now=NOW)]
        second = [(c.a, c.score) for c in rank(list(cands), now=NOW)]
        assert first == second

    def test_manual_strictly_outranks_attune_rec_at_equal_stats(self):
        manual = self._candidate("code-review", 5, 5, NOW - timedelta(days=2))
        auto = self._candidate("doc-audit", 5, 0, NOW - timedelta(days=2))
        ranked = rank([auto, manual], now=NOW)
        assert [c.a for c in ranked] == ["code-review", "doc-audit"]
        assert ranked[0].score > ranked[1].score  # strictly below, not tie-broken

    def test_months_old_burst_does_not_outrank_recent_pattern(self):
        old_burst = self._candidate("doc-audit", 7, 0, NOW - timedelta(days=90))
        recent = self._candidate("code-review", 5, 0, NOW - timedelta(days=1))
        ranked = rank([old_burst, recent], now=NOW)
        assert [c.a for c in ranked] == ["code-review", "doc-audit"]

    def test_tie_breaker_higher_support_then_lexical(self):
        a = self._candidate("b-flow", 5, 0, NOW)
        b = self._candidate("a-flow", 5, 0, NOW)
        ranked = rank([a, b], now=NOW)
        assert [c.a for c in ranked] == ["a-flow", "b-flow"]


def _write_corpus(tmp_path: Path, records: list[RunRecord]) -> Path:
    f = tmp_path / "runs.jsonl"
    lines = [
        json.dumps(
            {
                "workflow_name": r.workflow,
                "started_at": r.started_at.isoformat(),
                "trigger": r.trigger,
                "project": r.project,
                "run_id": r.run_id,
            }
        )
        for r in records
    ]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


class TestReadinessGate:
    """RR-1: the learner never proposes over an unready corpus."""

    def test_insufficient_corpus_proposes_nothing(self, tmp_path):
        records = [_rec("code-review", BASE), _rec("security-audit", BASE + timedelta(minutes=5))]
        report = learn(PROJECT, paths=[_write_corpus(tmp_path, records)], now=NOW)
        assert "insufficient corpus — not yet viable" in report.status
        assert report.candidates == []
        assert not report.readiness.viable

    def test_viable_corpus_reports_and_proposes(self, tmp_path):
        report = learn(PROJECT, paths=[_write_corpus(tmp_path, _seven_pair_corpus())], now=NOW)
        assert report.readiness.viable
        assert report.readiness.eligible_records == 18
        assert report.readiness.distinct_workflows == 4
        assert report.readiness.distinct_active_days == 7
        assert report.status == "proposing 1 candidate(s)"
        assert report.candidates[0].fingerprint() == "code-review->security-audit@w30"

    def test_readiness_requires_a_pair_at_min_support(self, tmp_path):
        # Plenty of records + days, but no repeated sequence.
        records = [
            _rec(w, BASE + timedelta(days=d, hours=h))
            for d in range(8)
            for h, w in [(0, "code-review"), (8, "doc-audit")]  # 8h gap: no pair
        ]
        report = learn(PROJECT, paths=[_write_corpus(tmp_path, records)], now=NOW)
        assert "no candidate pair at min-support" in report.status


class TestDecisions:
    """RR-6: opt-in, durable, idempotent decision state."""

    def _one_candidate(self, tmp_path: Path) -> tuple[LearnerReport, Path]:
        corpus = _write_corpus(tmp_path, _seven_pair_corpus())
        ledger = tmp_path / "ledger.jsonl"
        return learn(PROJECT, paths=[corpus], ledger=ledger, now=NOW), ledger

    def test_learn_produces_zero_artifact_writes(self, tmp_path):
        pipelines_dir = tmp_path / "pipelines"
        report, ledger = self._one_candidate(tmp_path)
        assert report.candidates  # it proposed…
        assert not pipelines_dir.exists()  # …and wrote no artifacts
        assert not ledger.exists()  # …and no ledger entries either

    def test_accepted_fingerprint_not_reproposed(self, tmp_path):
        report, ledger = self._one_candidate(tmp_path)
        cand = report.candidates[0]
        record_decision(cand.fingerprint(), "accepted", support=cand.support, path=ledger)
        rerun = learn(
            PROJECT, paths=[_write_corpus(tmp_path, _seven_pair_corpus())], ledger=ledger, now=NOW
        )
        assert rerun.candidates == []

    def test_declined_reopens_only_on_support_delta(self, tmp_path):
        report, ledger = self._one_candidate(tmp_path)
        cand = report.candidates[0]
        record_decision(cand.fingerprint(), "declined", support=cand.support, path=ledger)
        # Same evidence → stays closed.
        rerun = learn(
            PROJECT, paths=[_write_corpus(tmp_path, _seven_pair_corpus())], ledger=ledger, now=NOW
        )
        assert rerun.candidates == []
        # Support grows by the stated delta (+3) → reopens.
        grown = _seven_pair_corpus()
        for day in range(7, 10):
            at = BASE + timedelta(days=day)
            grown.append(_rec("code-review", at))
            grown.append(_rec("security-audit", at + timedelta(minutes=5)))
        reopened = learn(PROJECT, paths=[_write_corpus(tmp_path, grown)], ledger=ledger, now=NOW)
        assert [c.fingerprint() for c in reopened.candidates] == [cand.fingerprint()]

    def test_invalid_decision_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="decision must be one of"):
            record_decision("x->y@w30", "maybe", support=5, path=tmp_path / "l.jsonl")

    def test_ledger_path_resolves_under_attune_home(self):
        # The suite's ATTUNE_HOME isolation fixture must contain it.
        import os

        assert str(ledger_path()).startswith(os.environ["ATTUNE_HOME"])
        assert load_decisions() == {}


class TestScaffold:
    """RR-7: atomic, validated, contained acceptance artifacts."""

    def _candidate(self) -> Candidate:
        return Candidate(
            a="code-review",
            b="security-audit",
            support=7,
            a_occurrences=7,
            manual_pairs=6,
            last_pair_at=NOW,
            sample_run_ids=["r1", "r2"],
        )

    def test_acceptance_writes_yaml_and_evidence(self, tmp_path):
        yaml_path, evidence_path = scaffold_acceptance(
            self._candidate(), "review-then-audit", tmp_path / "pipelines"
        )
        assert yaml_path.is_file() and evidence_path.is_file()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["support"] == 7
        assert evidence["members"] == ["code-review", "security-audit"]
        assert evidence["sample_run_ids"] == ["r1", "r2"]
        assert evidence["provenance_mix"] == {"manual_pairs": 6, "auto_or_unknown_pairs": 1}

    def test_scaffold_yaml_is_well_formed(self, tmp_path):
        yaml = pytest.importorskip("yaml")
        yaml_path, _ = scaffold_acceptance(self._candidate(), "wf-pair", tmp_path / "p")
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert doc["name"] == "wf-pair"
        assert doc["kind"] == "pipeline"
        assert doc["members"] == ["code-review", "security-audit"]
        assert doc["window_minutes"] == 30

    def test_unknown_member_workflow_rejected(self, tmp_path):
        bad = self._candidate()
        bad.b = "not-a-registered-workflow"
        with pytest.raises(ScaffoldError, match="unknown workflows"):
            scaffold_acceptance(bad, "nope", tmp_path / "p")
        assert not (tmp_path / "p" / "nope.yaml").exists()

    @pytest.mark.parametrize("name", ["../escape", "Evil", "a/b", "", "-lead", "x" * 70])
    def test_unsafe_names_rejected(self, tmp_path, name):
        with pytest.raises(ScaffoldError):
            scaffold_acceptance(self._candidate(), name, tmp_path / "p")

    def test_collision_refused_nothing_overwritten(self, tmp_path):
        target = tmp_path / "p"
        scaffold_acceptance(self._candidate(), "dup-name", target)
        before = (target / "dup-name.yaml").read_text(encoding="utf-8")
        with pytest.raises(ScaffoldError, match="already scaffolded"):
            scaffold_acceptance(self._candidate(), "dup-name", target)
        assert (target / "dup-name.yaml").read_text(encoding="utf-8") == before

    def test_registry_is_never_mutated(self):
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        assert "review-then-audit" not in _DEFAULT_WORKFLOW_NAMES

    def test_containment_escape_detected(self, tmp_path, monkeypatch):
        # _NAME_RE already blocks path metacharacters, so the containment
        # check (RR-7 defense-in-depth) can't be triggered through a
        # regex-valid name alone. Force Path.resolve() to disagree for the
        # yaml destination only, to exercise the belt-and-suspenders guard.
        pipelines_dir = tmp_path / "pipelines"
        expected_yaml = pipelines_dir / "escape-test.yaml"
        original_resolve = Path.resolve

        def fake_resolve(self, *args, **kwargs):
            if self == expected_yaml:
                return Path("/outside/escape-test.yaml")
            return original_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", fake_resolve)
        with pytest.raises(ScaffoldError, match="escapes the pipelines directory"):
            scaffold_acceptance(self._candidate(), "escape-test", pipelines_dir)

    def test_partial_write_failure_rolls_back_both_or_neither(self, tmp_path, monkeypatch):
        # Simulate an OSError landing the yaml half but failing the
        # evidence half — the rollback must remove BOTH tmp files and the
        # already-replaced yaml destination (RR-7 both-or-neither).
        pipelines_dir = tmp_path / "pipelines"
        evidence_dest = pipelines_dir / "rollback-test.evidence.json"
        original_replace = Path.replace

        def fake_replace(self, target):
            if self.name == evidence_dest.name + ".tmp":
                raise OSError("simulated disk failure")
            return original_replace(self, target)

        monkeypatch.setattr(Path, "replace", fake_replace)
        with pytest.raises(OSError, match="simulated disk failure"):
            scaffold_acceptance(self._candidate(), "rollback-test", pipelines_dir)

        assert not (pipelines_dir / "rollback-test.yaml").exists()
        assert not evidence_dest.exists()
        assert not (pipelines_dir / "rollback-test.yaml.tmp").exists()
        assert not (pipelines_dir / "rollback-test.evidence.json.tmp").exists()
