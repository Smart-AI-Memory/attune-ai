"""ExecutionStrategy base seams (feature-lead pilot QA pass, #1569).

Covers `_execute_agent`'s real-tool dispatch table — every branch
maps an agent id/role to a Real* analyzer and reshapes its report
into the workflow-facing output dict — plus the exception fallback
and `_aggregate_results`. The Real* classes are stubbed at their
import site (`attune.orchestration.real_tools`); no subprocess, no
filesystem scans.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from attune.orchestration import real_tools
from attune.orchestration._strategies.base import ExecutionStrategy


class OneShot(ExecutionStrategy):
    """Minimal concrete strategy — the ABC needs execute() defined."""

    async def execute(self, agents, context):  # pragma: no cover - unused
        raise NotImplementedError


def agent(agent_id: str, role: str = "generic role") -> SimpleNamespace:
    return SimpleNamespace(id=agent_id, role=role)


def run(agent_stub, context: dict[str, Any] | None = None):
    return asyncio.run(OneShot()._execute_agent(agent_stub, context or {}))


def analyzer_returning(report):
    """A Real*-shaped class whose analyze/audit returns ``report``."""

    class Fake:
        def __init__(self, project_root):
            self.project_root = project_root

        def audit(self, target):
            return report

        def analyze(self, target=None):
            return report

    return Fake


class TestDispatchBranches:
    def test_security_branch_maps_report(self, monkeypatch):
        report = SimpleNamespace(
            total_issues=3,
            critical_count=1,
            high_count=1,
            medium_count=1,
            passed=False,
            issues_by_file={"a.py": 3},
        )
        monkeypatch.setattr(real_tools, "RealSecurityAuditor", analyzer_returning(report))
        result = run(agent("security_auditor", "Security Auditor"))
        assert result.success is False
        assert result.output["critical_issues"] == 1
        assert result.output["total_issues"] == 3
        assert result.confidence == 0.7  # issues present

    def test_security_clean_run_full_confidence_via_role(self, monkeypatch):
        report = SimpleNamespace(
            total_issues=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            passed=True,
            issues_by_file={},
        )
        monkeypatch.setattr(real_tools, "RealSecurityAuditor", analyzer_returning(report))
        # role-based dispatch: unknown id, "security" in role
        result = run(agent("custom-1", "App Security Reviewer"))
        assert result.success is True
        assert result.confidence == 1.0

    def test_coverage_branch_thresholds(self, monkeypatch):
        report = SimpleNamespace(total_coverage=72.0, files_analyzed=10, uncovered_files=["x.py"])
        monkeypatch.setattr(real_tools, "RealCoverageAnalyzer", analyzer_returning(report))
        result = run(agent("test_coverage_analyzer", "Coverage"))
        assert result.success is False  # < 80
        assert result.output["coverage_percent"] == 72.0
        assert result.confidence == pytest.approx(0.72)

    def test_quality_branch(self, monkeypatch):
        report = SimpleNamespace(
            quality_score=8.5, ruff_issues=2, mypy_issues=0, total_files=5, passed=True
        )
        monkeypatch.setattr(real_tools, "RealCodeQualityAnalyzer", analyzer_returning(report))
        result = run(agent("code_reviewer", "Quality Reviewer"))
        assert result.success is True
        assert result.output["quality_score"] == 8.5
        assert result.confidence == pytest.approx(0.85)

    def test_documentation_branch(self, monkeypatch):
        report = SimpleNamespace(
            completeness_percentage=90.0,
            total_functions=10,
            documented_functions=9,
            total_classes=2,
            documented_classes=2,
            missing_docstrings=["f"],
            passed=True,
        )
        monkeypatch.setattr(real_tools, "RealDocumentationAnalyzer", analyzer_returning(report))
        result = run(agent("documentation_writer", "Documentation"))
        assert result.output["coverage_percent"] == 90.0  # release-prep field alias
        assert result.confidence == pytest.approx(0.9)

    def test_performance_branch(self, monkeypatch):
        report = SimpleNamespace(
            score=6.0,
            total_files=4,
            functions_analyzed=40,
            high_complexity=["f1"],
            large_functions=["f2", "f3"],
            passed=False,
        )
        monkeypatch.setattr(real_tools, "RealPerformanceProfiler", analyzer_returning(report))
        result = run(agent("performance_optimizer", "Performance"))
        assert result.success is False
        assert result.output["high_complexity_count"] == 1
        assert result.output["large_functions_count"] == 2
        assert result.confidence == pytest.approx(0.6)

    def test_architecture_branch(self, monkeypatch):
        report = SimpleNamespace(
            score=9.0,
            total_modules=30,
            total_packages=6,
            max_depth=4,
            circular_imports=[],
            high_coupling=["m"],
            passed=True,
        )
        monkeypatch.setattr(real_tools, "RealArchitectureAnalyzer", analyzer_returning(report))
        result = run(agent("architecture_analyst", "Architecture"))
        assert result.output["circular_imports"] == 0
        assert result.output["high_coupling_count"] == 1
        assert result.confidence == pytest.approx(0.9)

    def test_test_generator_placeholder(self):
        result = run(agent("test_generator", "Test Generator"))
        assert result.success is True
        assert "manual invocation" in result.output["message"]
        assert result.confidence == 0.8

    def test_unknown_agent_placeholder(self):
        result = run(agent("mystery", "Mystery Role"))
        assert result.success is True
        assert result.output["agent_id"] == "mystery"
        assert result.confidence == 0.5

    def test_context_paths_reach_the_analyzer(self, monkeypatch):
        seen = {}

        class Probe:
            def __init__(self, project_root):
                seen["root"] = project_root

            def audit(self, target):
                seen["target"] = target
                return SimpleNamespace(
                    total_issues=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    passed=True,
                    issues_by_file={},
                )

        monkeypatch.setattr(real_tools, "RealSecurityAuditor", Probe)
        run(agent("security_auditor"), {"project_root": "/repo", "target_path": "pkg"})
        assert seen == {"root": "/repo", "target": "pkg"}

    def test_analyzer_exception_becomes_failed_result(self, monkeypatch):
        class Boom:
            def __init__(self, project_root):
                raise RuntimeError("tool exploded")

        monkeypatch.setattr(real_tools, "RealSecurityAuditor", Boom)
        result = run(agent("security_auditor"))
        assert result.success is False
        assert result.error == "tool exploded"
        assert result.confidence == 0.0
        assert result.output["error_details"] == "tool exploded"
        assert result.duration_seconds >= 0


class TestAggregateResults:
    def test_aggregates_success_and_confidence(self):
        results = [
            SimpleNamespace(success=True, confidence=1.0, output={"a": 1}),
            SimpleNamespace(success=False, confidence=0.5, output={"b": 2}),
        ]
        agg = OneShot()._aggregate_results(results)
        assert agg["num_agents"] == 2
        assert agg["all_succeeded"] is False
        assert agg["avg_confidence"] == pytest.approx(0.75)
        assert agg["outputs"] == [{"a": 1}, {"b": 2}]

    def test_empty_results_zero_confidence(self):
        agg = OneShot()._aggregate_results([])
        assert agg == {
            "num_agents": 0,
            "all_succeeded": True,
            "avg_confidence": 0.0,
            "outputs": [],
        }
