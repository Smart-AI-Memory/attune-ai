"""Tests for the DiscoverySweepEngine orchestrator and BudgetTracker."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep import (
    BudgetTracker,
    DiscoverySweepEngine,
    Finding,
    ResolutionComplexity,
    Severity,
    SweepBudgetExceeded,
    SweepResult,
    VerificationEngine,
    VerificationStatus,
    read_jsonl,
    split_findings_by_complexity,
)
from attune.workflows.discovery_sweep.rules import default_rules

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@dataclass
class _MockSource:
    """A FindingSource double that emits canned findings."""

    name: str
    findings: list[Finding]
    estimated_spend_usd: float = 0.0
    raise_on_discover: Exception | None = None
    calls: int = 0

    def discover(self, scope: Path, budget_usd: float, sweep_id: str) -> Iterable[Finding]:
        self.calls += 1
        if self.raise_on_discover is not None:
            raise self.raise_on_discover
        # Stamp the sweep_id on each emitted finding so the
        # orchestrator's audit trail propagates.
        return [
            Finding(
                source_workflow=f.source_workflow,
                file_path=f.file_path,
                severity=f.severity,
                message=f.message,
                raw_finding=f.raw_finding,
                sweep_id=sweep_id,
                line=f.line,
            )
            for f in self.findings
        ]


def _seed_finding(
    *,
    source: str = "bug_predict",
    file_path: str = "src/attune/example.py",
    message: str = "unknown finding",
    line: int = 10,
    severity: Severity = Severity.MEDIUM,
) -> Finding:
    return Finding(
        source_workflow=source,
        file_path=file_path,
        severity=severity,
        message=message,
        raw_finding={"pattern": "x"},
        sweep_id="placeholder",
        line=line,
    )


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------


class TestBudgetTracker:
    def test_defaults_match_spec(self):
        tracker = BudgetTracker()
        assert tracker.subworkflow_cap_usd == pytest.approx(10.0)
        assert tracker.sweep_cap_usd == pytest.approx(40.0)

    def test_budget_for_starts_at_subworkflow_cap(self):
        tracker = BudgetTracker()
        assert tracker.budget_for("any") == pytest.approx(10.0)

    def test_record_accumulates_spend(self):
        tracker = BudgetTracker()
        tracker.record("bug_predict", 3.5)
        tracker.record("security_audit", 2.0)
        assert tracker.total_spend_usd == pytest.approx(5.5)
        assert tracker.remaining_sweep_usd == pytest.approx(34.5)

    def test_record_raises_when_ceiling_exceeded(self):
        tracker = BudgetTracker(sweep_cap_usd=20.0, subworkflow_cap_usd=10.0)
        tracker.record("a", 9.0)
        tracker.record("b", 9.0)
        with pytest.raises(SweepBudgetExceeded):
            tracker.record("c", 9.0)
        # Spend was still recorded so the audit log captures it.
        assert tracker.total_spend_usd == pytest.approx(27.0)

    def test_can_run_returns_false_after_ceiling(self):
        tracker = BudgetTracker(sweep_cap_usd=5.0, subworkflow_cap_usd=10.0)
        with pytest.raises(SweepBudgetExceeded):
            tracker.record("a", 10.0)
        assert not tracker.can_run("b")

    def test_from_env_respects_overrides(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD", "5.0")
        monkeypatch.setenv("ATTUNE_DISCOVERY_SWEEP_BUDGET_USD", "15.0")
        tracker = BudgetTracker.from_env()
        assert tracker.subworkflow_cap_usd == pytest.approx(5.0)
        assert tracker.sweep_cap_usd == pytest.approx(15.0)

    def test_from_env_falls_back_on_invalid_value(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD", "not-a-number")
        tracker = BudgetTracker.from_env()
        assert tracker.subworkflow_cap_usd == pytest.approx(10.0)

    def test_explicit_kwargs_override_env(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_DISCOVERY_SWEEP_BUDGET_USD", "100.0")
        tracker = BudgetTracker.from_env(sweep_cap_usd=7.5)
        assert tracker.sweep_cap_usd == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# DiscoverySweepEngine — orchestration
# ---------------------------------------------------------------------------


class TestSweepOrchestration:
    def test_requires_at_least_one_source(self):
        with pytest.raises(ValueError):
            DiscoverySweepEngine(sources=[])

    def test_aggregates_findings_from_multiple_sources(self, tmp_path):
        bug_source = _MockSource(
            name="bug_predict",
            findings=[
                _seed_finding(
                    file_path=str(tmp_path / "real_eval.py"),
                    message="dangerous_eval detected",
                )
            ],
            estimated_spend_usd=2.0,
        )
        sec_source = _MockSource(
            name="security_audit",
            findings=[
                _seed_finding(
                    source="security_audit",
                    file_path=str(tmp_path / "auth.py"),
                    message="missing path validation",
                )
            ],
            estimated_spend_usd=3.0,
        )

        workflow = DiscoverySweepEngine(
            sources=[bug_source, sec_source],
            output_dir=tmp_path / "out",
            project_root=tmp_path,
        )
        result = workflow.run(scope=tmp_path)

        assert isinstance(result, SweepResult)
        assert bug_source.calls == 1
        assert sec_source.calls == 1
        # Both findings flow into one of the three files; total
        # count across the three lists matches input count.
        assert result.accept_count + result.reject_count + result.unsure_count == 2

    def test_writes_three_output_files(self, tmp_path):
        source = _MockSource(
            name="bug_predict",
            findings=[_seed_finding(message="unknown pattern")],
        )
        workflow = DiscoverySweepEngine(
            sources=[source],
            output_dir=tmp_path / "queue",
            project_root=tmp_path,
        )
        result = workflow.run(scope=tmp_path)

        assert result.queue_path is not None
        assert result.rejected_path is not None
        assert result.questions_path is not None
        assert Path(result.queue_path).exists()
        assert Path(result.rejected_path).exists()
        assert Path(result.questions_path).exists()

    def test_sweep_id_consistent_across_files(self, tmp_path):
        source = _MockSource(
            name="bug_predict",
            findings=[
                _seed_finding(message="memory_leak: dirs[:]"),
                _seed_finding(message="unknown finding"),
            ],
        )
        workflow = DiscoverySweepEngine(
            sources=[source],
            output_dir=tmp_path / "queue",
            project_root=tmp_path,
        )
        result = workflow.run(scope=tmp_path)

        queue_findings = read_jsonl(result.queue_path)
        rejected_findings = read_jsonl(result.rejected_path)
        all_emitted = queue_findings + rejected_findings
        for finding in all_emitted:
            assert finding.sweep_id == result.sweep_id
        # And the markdown file's header contains the sweep_id too.
        md = Path(result.questions_path).read_text()
        assert result.sweep_id in md

    def test_one_source_failure_does_not_abort_sweep(self, tmp_path):
        good_source = _MockSource(
            name="bug_predict",
            findings=[_seed_finding(message="good finding")],
        )
        bad_source = _MockSource(
            name="security_audit",
            findings=[],
            raise_on_discover=RuntimeError("adapter exploded"),
        )

        workflow = DiscoverySweepEngine(
            sources=[bad_source, good_source],
            output_dir=tmp_path / "out",
            project_root=tmp_path,
        )
        result = workflow.run(scope=tmp_path)

        # The good source's finding still flows through.
        assert (result.accept_count + result.reject_count + result.unsure_count) == 1
        # The failure is recorded by source name.
        assert "security_audit" in result.sub_workflow_errors
        assert "adapter exploded" in result.sub_workflow_errors["security_audit"]

    def test_budget_ceiling_halts_further_sources(self, tmp_path):
        # First source spends nearly the whole sweep cap; second
        # source should be skipped.
        source_one = _MockSource(
            name="bug_predict",
            findings=[_seed_finding(message="one")],
            estimated_spend_usd=12.0,
        )
        source_two = _MockSource(
            name="security_audit",
            findings=[_seed_finding(message="two")],
            estimated_spend_usd=1.0,
        )

        budget = BudgetTracker(sweep_cap_usd=10.0, subworkflow_cap_usd=12.0)
        workflow = DiscoverySweepEngine(
            sources=[source_one, source_two],
            output_dir=tmp_path / "out",
            project_root=tmp_path,
            budget=budget,
        )
        result = workflow.run(scope=tmp_path)

        assert result.budget_halted is True
        assert source_two.calls == 0
        # Source one's spend is recorded, even though it crossed the cap.
        assert "bug_predict" in result.sub_workflow_spend

    def test_no_findings_still_writes_empty_files(self, tmp_path):
        source = _MockSource(name="bug_predict", findings=[])
        workflow = DiscoverySweepEngine(
            sources=[source],
            output_dir=tmp_path / "out",
            project_root=tmp_path,
        )
        result = workflow.run(scope=tmp_path)

        assert result.accept_count == 0
        assert Path(result.queue_path).read_text() == ""
        assert Path(result.rejected_path).read_text() == ""
        assert "No UNSURE findings" in Path(result.questions_path).read_text()


# ---------------------------------------------------------------------------
# End-to-end verification flow through the orchestrator
# ---------------------------------------------------------------------------


class TestSweepWithRealVerification:
    """The orchestrator wires verification + complexity by default;
    these tests confirm a finding that the rule engine REJECTs
    lands in the rejected file (not the queue or questions)."""

    def test_known_false_positive_lands_in_rejected(self, tmp_path):
        # Synthesize a fixture file with the os.walk + dirs[:] pattern.
        fixture = tmp_path / "walker.py"
        fixture.write_text(
            "import os\n"
            "\n"
            "def find_py(root):\n"
            "    matches = []\n"
            "    for dirpath, dirs, files in os.walk(root):\n"
            "        dirs[:] = [d for d in dirs if d != '.git']\n"
            "        matches.extend(files)\n"
            "    return matches\n"
        )
        # The "scanner" emits a finding pointing at the dirs[:] line.
        # Discovery files are stored as relative paths so the
        # verification engine resolves them against the project root.
        finding = _seed_finding(
            file_path=str(fixture.relative_to(tmp_path)),
            message="memory_leak: large_list_copy on dirs[:]",
            line=6,  # dirs[:] line
        )
        source = _MockSource(name="perf_audit", findings=[finding])

        workflow = DiscoverySweepEngine(
            sources=[source],
            output_dir=tmp_path / "out",
            project_root=tmp_path,
            verification_engine=VerificationEngine(default_rules(), project_root=tmp_path),
        )
        result = workflow.run(scope=tmp_path)

        assert result.reject_count == 1
        assert result.accept_count == 0
        rejected = read_jsonl(result.rejected_path)
        assert len(rejected) == 1
        assert rejected[0].verification_status == VerificationStatus.REJECT
        assert "os.walk" in rejected[0].verification_reasoning


# ---------------------------------------------------------------------------
# split_findings_by_complexity
# ---------------------------------------------------------------------------


class TestSplitFindingsByComplexity:
    def test_partitions_accepts_by_tag(self):
        routine = Finding(
            source_workflow="bug_predict",
            file_path="src/attune/util.py",
            severity=Severity.MEDIUM,
            message="x",
            raw_finding={},
            sweep_id="s",
            line=1,
            verification_status=VerificationStatus.ACCEPT,
            resolution_complexity=ResolutionComplexity.ROUTINE,
        )
        sensitive = Finding(
            source_workflow="security_audit",
            file_path="src/attune/security/x.py",
            severity=Severity.HIGH,
            message="y",
            raw_finding={},
            sweep_id="s",
            line=2,
            verification_status=VerificationStatus.ACCEPT,
            resolution_complexity=ResolutionComplexity.NEEDS_PATRICK,
        )
        unrelated = Finding(
            source_workflow="bug_predict",
            file_path="src/attune/util.py",
            severity=Severity.LOW,
            message="z",
            raw_finding={},
            sweep_id="s",
            line=3,
            verification_status=VerificationStatus.UNSURE,
        )

        routine_out, needs_patrick_out = split_findings_by_complexity(
            [routine, sensitive, unrelated]
        )
        assert routine_out == [routine]
        assert needs_patrick_out == [sensitive]
