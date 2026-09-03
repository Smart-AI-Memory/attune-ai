"""Tests for release_prep_team module.

Tests ReleasePrepTeam coordination, quality gate evaluation,
issue identification, and ReleasePrepTeamWorkflow adapter.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# Minimal stubs for release_models types to avoid importing Redis/Anthropic
@dataclass
class FakeAgentResult:
    agent_role: str
    success: bool
    score: float
    findings: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeQualityGate:
    name: str
    threshold: float
    actual: float
    passed: bool
    critical: bool

    @property
    def message(self) -> str:
        return f"{self.actual:.1f} vs {self.threshold:.1f}"


@dataclass
class FakeReadinessReport:
    approved: bool
    confidence: str
    quality_gates: list = field(default_factory=list)
    agent_results: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    summary: str = ""
    total_duration: float = 0.0
    total_cost: float = 0.0

    def format_console_output(self) -> str:
        return self.summary


# ---------------------------------------------------------------------------
# Tests for _evaluate_quality_gates
# ---------------------------------------------------------------------------


class TestEvaluateQualityGates:
    """Tests for ReleasePrepTeam._evaluate_quality_gates."""

    def _make_team(self, quality_gates=None):
        """Create a ReleasePrepTeam with mocked dependencies."""
        with (
            patch("attune.agents.release.release_prep_team.REDIS_AVAILABLE", False),
            patch("attune.agents.release.release_prep_team.SecurityAuditorAgent"),
            patch("attune.agents.release.release_prep_team.TestCoverageAgent"),
            patch("attune.agents.release.release_prep_team.CodeQualityAgent"),
            patch("attune.agents.release.release_prep_team.DocumentationAgent"),
        ):
            from attune.agents.release.release_prep_team import ReleasePrepTeam

            team = ReleasePrepTeam(quality_gates=quality_gates)
            return team

    def test_all_gates_pass(self):
        """When all agent results meet thresholds, all gates pass."""
        team = self._make_team()

        results = [
            FakeAgentResult("Security Auditor", True, 9.0, {"critical_issues": 0}),
            FakeAgentResult("Test Coverage", True, 9.0, {"coverage_percent": 85.0}),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 9.0, {"coverage_percent": 90.0}),
        ]

        gates = team._evaluate_quality_gates(results)

        assert len(gates) == 4
        assert all(g.passed for g in gates)

    def test_security_gate_fails_on_critical_issues(self):
        """Security gate fails when critical issues > 0."""
        team = self._make_team()

        results = [
            FakeAgentResult("Security Auditor", True, 2.0, {"critical_issues": 3}),
            FakeAgentResult("Test Coverage", True, 9.0, {"coverage_percent": 90.0}),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 9.0, {"coverage_percent": 90.0}),
        ]

        gates = team._evaluate_quality_gates(results)
        security_gate = next(g for g in gates if g.name == "Security")

        assert not security_gate.passed
        assert security_gate.critical is True

    def test_coverage_gate_fails_below_threshold(self):
        """Coverage gate fails when below min_coverage."""
        team = self._make_team()

        results = [
            FakeAgentResult("Security Auditor", True, 9.0, {"critical_issues": 0}),
            FakeAgentResult("Test Coverage", True, 5.0, {"coverage_percent": 50.0}),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 9.0, {"coverage_percent": 90.0}),
        ]

        gates = team._evaluate_quality_gates(results)
        coverage_gate = next(g for g in gates if g.name == "Test Coverage")

        assert not coverage_gate.passed

    def test_coverage_gate_fails_when_result_is_estimated(self):
        """Estimated coverage cannot approve the critical release gate."""
        team = self._make_team()

        results = [
            FakeAgentResult("Security Auditor", True, 9.0, {"critical_issues": 0}),
            FakeAgentResult(
                "Test Coverage",
                True,
                9.0,
                {"coverage_percent": 85.0, "estimated": True},
            ),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 9.0, {"coverage_percent": 90.0}),
        ]

        gates = team._evaluate_quality_gates(results)
        coverage_gate = next(g for g in gates if g.name == "Test Coverage")

        assert coverage_gate.actual == pytest.approx(85.0)
        assert coverage_gate.passed is False

    def test_documentation_gate_not_critical(self):
        """Documentation gate is non-critical (warning only)."""
        team = self._make_team()

        results = [
            FakeAgentResult("Security Auditor", True, 9.0, {"critical_issues": 0}),
            FakeAgentResult("Test Coverage", True, 9.0, {"coverage_percent": 90.0}),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 3.0, {"coverage_percent": 30.0}),
        ]

        gates = team._evaluate_quality_gates(results)
        doc_gate = next(g for g in gates if g.name == "Documentation")

        assert not doc_gate.passed
        assert doc_gate.critical is False

    def test_custom_quality_gates(self):
        """Custom quality gates override defaults."""
        team = self._make_team(quality_gates={"min_coverage": 95.0})

        results = [
            FakeAgentResult("Security Auditor", True, 9.0, {"critical_issues": 0}),
            FakeAgentResult("Test Coverage", True, 9.0, {"coverage_percent": 90.0}),
            FakeAgentResult("Code Quality", True, 9.0, {"quality_score": 8.0}),
            FakeAgentResult("Documentation", True, 9.0, {"coverage_percent": 90.0}),
        ]

        gates = team._evaluate_quality_gates(results)
        coverage_gate = next(g for g in gates if g.name == "Test Coverage")

        # 90% < 95% threshold
        assert not coverage_gate.passed


# ---------------------------------------------------------------------------
# Tests for _identify_issues
# ---------------------------------------------------------------------------


class TestIdentifyIssues:
    """Tests for ReleasePrepTeam._identify_issues."""

    def _make_team(self):
        with (
            patch("attune.agents.release.release_prep_team.REDIS_AVAILABLE", False),
            patch("attune.agents.release.release_prep_team.SecurityAuditorAgent"),
            patch("attune.agents.release.release_prep_team.TestCoverageAgent"),
            patch("attune.agents.release.release_prep_team.CodeQualityAgent"),
            patch("attune.agents.release.release_prep_team.DocumentationAgent"),
        ):
            from attune.agents.release.release_prep_team import ReleasePrepTeam

            return ReleasePrepTeam()

    def test_critical_gate_failure_is_blocker(self):
        """Failed critical gates produce blockers."""
        team = self._make_team()

        gates = [
            FakeQualityGate("Security", 0.0, 3.0, False, True),
        ]
        results = [FakeAgentResult("Security Auditor", True, 2.0, {})]

        blockers, warnings = team._identify_issues(gates, results)

        assert len(blockers) == 1
        assert "Security" in blockers[0]

    def test_noncritical_gate_failure_is_warning(self):
        """Failed non-critical gates produce warnings."""
        team = self._make_team()

        gates = [
            FakeQualityGate("Documentation", 80.0, 30.0, False, False),
        ]
        results = []

        blockers, warnings = team._identify_issues(gates, results)

        assert len(blockers) == 0
        assert len(warnings) == 1
        assert "Documentation" in warnings[0]

    def test_agent_error_adds_blocker(self):
        """Agent failure with error adds a blocker."""
        team = self._make_team()

        gates = []
        results = [
            FakeAgentResult("Security Auditor", False, 0.0, {"error": "Bandit crashed"}),
        ]

        blockers, warnings = team._identify_issues(gates, results)

        assert len(blockers) == 1
        assert "Bandit crashed" in blockers[0]


# ---------------------------------------------------------------------------
# Tests for _generate_summary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    """Tests for ReleasePrepTeam._generate_summary."""

    def _make_team(self):
        with (
            patch("attune.agents.release.release_prep_team.REDIS_AVAILABLE", False),
            patch("attune.agents.release.release_prep_team.SecurityAuditorAgent"),
            patch("attune.agents.release.release_prep_team.TestCoverageAgent"),
            patch("attune.agents.release.release_prep_team.CodeQualityAgent"),
            patch("attune.agents.release.release_prep_team.DocumentationAgent"),
        ):
            from attune.agents.release.release_prep_team import ReleasePrepTeam

            return ReleasePrepTeam()

    def test_approved_summary(self):
        """Approved release includes APPROVED text."""
        team = self._make_team()
        gates = [FakeQualityGate("Security", 0.0, 0.0, True, True)]
        results = [FakeAgentResult("Security Auditor", True, 9.0, {})]

        summary = team._generate_summary(True, gates, results)

        assert "RELEASE APPROVED" in summary

    def test_not_approved_summary(self):
        """Not-approved release includes NOT APPROVED text."""
        team = self._make_team()
        gates = [FakeQualityGate("Security", 0.0, 3.0, False, True)]
        results = [FakeAgentResult("Security Auditor", True, 2.0, {})]

        summary = team._generate_summary(False, gates, results)

        assert "RELEASE NOT APPROVED" in summary
        assert "Failed gates" in summary


# ---------------------------------------------------------------------------
# Tests for get_total_cost
# ---------------------------------------------------------------------------


class TestGetTotalCost:
    """Tests for ReleasePrepTeam.get_total_cost."""

    def test_sums_agent_costs(self):
        """Total cost is sum of all agent costs."""
        with (
            patch("attune.agents.release.release_prep_team.REDIS_AVAILABLE", False),
            patch("attune.agents.release.release_prep_team.SecurityAuditorAgent") as mock_sec,
            patch("attune.agents.release.release_prep_team.TestCoverageAgent") as mock_cov,
            patch("attune.agents.release.release_prep_team.CodeQualityAgent") as mock_qual,
            patch("attune.agents.release.release_prep_team.DocumentationAgent") as mock_doc,
        ):
            # Set total_cost on each mock agent instance
            mock_sec.return_value.total_cost = 0.01
            mock_cov.return_value.total_cost = 0.02
            mock_qual.return_value.total_cost = 0.03
            mock_doc.return_value.total_cost = 0.04

            from attune.agents.release.release_prep_team import ReleasePrepTeam

            team = ReleasePrepTeam()

            assert team.get_total_cost() == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Tests for ReleasePrepTeamWorkflow
# ---------------------------------------------------------------------------


class TestReleasePrepTeamWorkflow:
    """Tests for the BaseWorkflow adapter."""

    @pytest.mark.asyncio
    async def test_run_stage_raises(self):
        """run_stage() is not supported and raises NotImplementedError."""
        from attune.agents.release.release_prep_team import ReleasePrepTeamWorkflow

        wf = ReleasePrepTeamWorkflow()

        with pytest.raises(NotImplementedError):
            await wf.run_stage("triage", MagicMock(), None)

    def test_class_attributes(self):
        """Workflow has required class attributes for registry."""
        from attune.agents.release.release_prep_team import ReleasePrepTeamWorkflow

        assert ReleasePrepTeamWorkflow.name == "release-prep"
        assert len(ReleasePrepTeamWorkflow.stages) == 4
        assert "description" in dir(ReleasePrepTeamWorkflow)
