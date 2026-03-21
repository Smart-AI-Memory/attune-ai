"""Tests for the ExecutionStrategy base class.

Covers:
- _execute_agent dispatch for all agent types
- _aggregate_results aggregation logic
- Error handling in _execute_agent
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.orchestration._strategies.base import ExecutionStrategy
from attune.orchestration._strategies.data_classes import AgentResult, StrategyResult
from attune.orchestration.agent_templates import AgentTemplate, ResourceRequirements

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# The base module path where lazy imports resolve
_TOOLS_MOD = "attune.orchestration.real_tools"


def _make_agent(agent_id: str, role: str) -> AgentTemplate:
    """Build a minimal AgentTemplate for testing."""
    return AgentTemplate(
        id=agent_id,
        role=role,
        capabilities=["analyze"],
        tier_preference="CAPABLE",
        tools=["tool"],
        default_instructions="instructions",
        quality_gates={},
        resource_requirements=ResourceRequirements(timeout_seconds=30),
    )


class ConcreteStrategy(ExecutionStrategy):
    """Concrete subclass to test base class methods."""

    async def execute(self, agents, context):
        """Not tested here — just satisfies the ABC."""
        return StrategyResult(
            success=True,
            outputs=[],
            aggregated_output={},
        )


def _make_mock_report(**kwargs):
    """Build a MagicMock report with given attributes."""
    report = MagicMock()
    for k, v in kwargs.items():
        setattr(report, k, v)
    return report


# ------------------------------------------------------------------
# _execute_agent dispatch tests
# ------------------------------------------------------------------


class TestExecuteAgentDispatch:
    """Verify _execute_agent maps agent IDs to real tool classes."""

    @pytest.mark.asyncio
    async def test_security_auditor_by_id(self):
        """security_auditor agent ID dispatches to RealSecurityAuditor."""
        strategy = ConcreteStrategy()
        agent = _make_agent("security_auditor", "Security Expert")
        report = _make_mock_report(
            total_issues=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            passed=True,
            issues_by_file={},
        )

        with patch(f"{_TOOLS_MOD}.RealSecurityAuditor") as mock_cls:
            mock_cls.return_value.audit.return_value = report
            result = await strategy._execute_agent(
                agent, {"project_root": ".", "target_path": "src"}
            )

        assert result.success is True
        assert result.output["total_issues"] == 0
        assert result.confidence == 1.0
        mock_cls.assert_called_once_with(".")

    @pytest.mark.asyncio
    async def test_security_by_role(self):
        """Agent with 'security' in role dispatches to RealSecurityAuditor."""
        strategy = ConcreteStrategy()
        agent = _make_agent("custom_agent", "Security Reviewer")
        report = _make_mock_report(
            total_issues=2,
            critical_count=1,
            high_count=1,
            medium_count=0,
            passed=False,
            issues_by_file={"a.py": ["issue"]},
        )

        with patch(f"{_TOOLS_MOD}.RealSecurityAuditor") as mock_cls:
            mock_cls.return_value.audit.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is False
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_coverage_analyzer_by_id(self):
        """test_coverage_analyzer dispatches to RealCoverageAnalyzer."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_coverage_analyzer", "Coverage Expert")
        report = _make_mock_report(
            total_coverage=85.0,
            files_analyzed=10,
            uncovered_files=["b.py"],
        )

        with patch(f"{_TOOLS_MOD}.RealCoverageAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is True
        assert result.output["coverage_percent"] == 85.0
        assert result.confidence == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_coverage_below_threshold(self):
        """Coverage below 80% reports failure."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_coverage_analyzer", "Coverage Expert")
        report = _make_mock_report(
            total_coverage=60.0,
            files_analyzed=5,
            uncovered_files=["c.py"],
        )

        with patch(f"{_TOOLS_MOD}.RealCoverageAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is False
        assert result.output["passed"] is False

    @pytest.mark.asyncio
    async def test_code_reviewer_by_id(self):
        """code_reviewer dispatches to RealCodeQualityAnalyzer."""
        strategy = ConcreteStrategy()
        agent = _make_agent("code_reviewer", "Code Quality Expert")
        report = _make_mock_report(
            quality_score=9.0,
            ruff_issues=0,
            mypy_issues=0,
            total_files=20,
            passed=True,
        )

        with patch(f"{_TOOLS_MOD}.RealCodeQualityAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(
                agent, {"project_root": ".", "target_path": "src"}
            )

        assert result.success is True
        assert result.output["quality_score"] == 9.0
        assert result.confidence == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_documentation_writer_by_id(self):
        """documentation_writer dispatches to RealDocumentationAnalyzer."""
        strategy = ConcreteStrategy()
        agent = _make_agent("documentation_writer", "Documentation Expert")
        report = _make_mock_report(
            completeness_percentage=75.0,
            total_functions=20,
            documented_functions=15,
            total_classes=5,
            documented_classes=4,
            missing_docstrings=["func_a"],
            passed=False,
        )

        with patch(f"{_TOOLS_MOD}.RealDocumentationAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is False
        assert result.output["completeness"] == 75.0
        assert result.output["missing_docstrings"] == ["func_a"]

    @pytest.mark.asyncio
    async def test_performance_optimizer_by_id(self):
        """performance_optimizer dispatches to RealPerformanceProfiler."""
        strategy = ConcreteStrategy()
        agent = _make_agent("performance_optimizer", "Performance Expert")
        report = _make_mock_report(
            score=8.5,
            total_files=10,
            functions_analyzed=50,
            high_complexity=[],
            large_functions=[],
            passed=True,
        )

        with patch(f"{_TOOLS_MOD}.RealPerformanceProfiler") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is True
        assert result.output["score"] == 8.5
        assert result.output["high_complexity_count"] == 0

    @pytest.mark.asyncio
    async def test_architecture_analyst_by_id(self):
        """architecture_analyst dispatches to RealArchitectureAnalyzer."""
        strategy = ConcreteStrategy()
        agent = _make_agent("architecture_analyst", "Architecture Expert")
        report = _make_mock_report(
            score=7.0,
            total_modules=15,
            total_packages=3,
            max_depth=4,
            circular_imports=[],
            high_coupling=[],
            passed=True,
        )

        with patch(f"{_TOOLS_MOD}.RealArchitectureAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is True
        assert result.output["total_modules"] == 15
        assert result.output["circular_imports"] == 0

    @pytest.mark.asyncio
    async def test_test_generator_returns_placeholder(self):
        """test_generator returns a placeholder result (LLM-based)."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_generator", "Test Generator")

        result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is True
        assert result.confidence == 0.8
        assert "manual invocation" in result.output["message"]

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_placeholder(self):
        """Unknown agent ID returns a placeholder with low confidence."""
        strategy = ConcreteStrategy()
        agent = _make_agent("totally_new_agent", "Brand New Role")

        result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is True
        assert result.confidence == 0.5
        assert result.output["agent_id"] == "totally_new_agent"

    @pytest.mark.asyncio
    async def test_exception_returns_error_result(self):
        """An exception in the tool returns an AgentResult with error."""
        strategy = ConcreteStrategy()
        agent = _make_agent("security_auditor", "Security Expert")

        with patch(f"{_TOOLS_MOD}.RealSecurityAuditor") as mock_cls:
            mock_cls.return_value.audit.side_effect = RuntimeError("disk full")
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.success is False
        assert result.error == "disk full"
        assert result.confidence == 0.0
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_uses_context_paths(self):
        """project_root and target_path are read from context."""
        strategy = ConcreteStrategy()
        agent = _make_agent("code_reviewer", "Quality Expert")
        report = _make_mock_report(
            quality_score=10.0,
            ruff_issues=0,
            mypy_issues=0,
            total_files=1,
            passed=True,
        )

        with patch(f"{_TOOLS_MOD}.RealCodeQualityAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            await strategy._execute_agent(
                agent,
                {"project_root": "/my/project", "target_path": "lib"},
            )

        mock_cls.assert_called_once_with("/my/project")
        mock_cls.return_value.analyze.assert_called_once_with("lib")

    @pytest.mark.asyncio
    async def test_default_context_values(self):
        """Default project_root='.' and target_path='src' when absent."""
        strategy = ConcreteStrategy()
        agent = _make_agent("code_reviewer", "Quality Expert")
        report = _make_mock_report(
            quality_score=10.0,
            ruff_issues=0,
            mypy_issues=0,
            total_files=1,
            passed=True,
        )

        with patch(f"{_TOOLS_MOD}.RealCodeQualityAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            await strategy._execute_agent(agent, {})

        mock_cls.assert_called_once_with(".")
        mock_cls.return_value.analyze.assert_called_once_with("src")

    @pytest.mark.asyncio
    async def test_coverage_confidence_capped_at_one(self):
        """Coverage confidence is capped at 1.0 even for >100% values."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_coverage_analyzer", "Coverage Expert")
        report = _make_mock_report(
            total_coverage=120.0,
            files_analyzed=1,
            uncovered_files=[],
        )

        with patch(f"{_TOOLS_MOD}.RealCoverageAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.return_value = report
            result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_result_has_agent_id(self):
        """Every AgentResult has the correct agent_id."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_generator", "Test Gen")

        result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.agent_id == "test_generator"

    @pytest.mark.asyncio
    async def test_result_has_positive_duration(self):
        """AgentResult has a non-negative duration."""
        strategy = ConcreteStrategy()
        agent = _make_agent("test_generator", "Test Gen")

        result = await strategy._execute_agent(agent, {"project_root": "."})

        assert result.duration_seconds >= 0


# ------------------------------------------------------------------
# _aggregate_results tests
# ------------------------------------------------------------------


class TestAggregateResults:
    """Tests for _aggregate_results."""

    def test_empty_results(self):
        """Empty list returns zero counts."""
        strategy = ConcreteStrategy()
        agg = strategy._aggregate_results([])

        assert agg["num_agents"] == 0
        assert agg["all_succeeded"] is True  # vacuous truth
        assert agg["avg_confidence"] == 0.0
        assert agg["outputs"] == []

    def test_all_succeeded(self):
        """All-success results report all_succeeded=True."""
        strategy = ConcreteStrategy()
        results = [
            AgentResult(agent_id="a", success=True, output={"x": 1}, confidence=0.9),
            AgentResult(agent_id="b", success=True, output={"x": 2}, confidence=0.7),
        ]
        agg = strategy._aggregate_results(results)

        assert agg["num_agents"] == 2
        assert agg["all_succeeded"] is True
        assert agg["avg_confidence"] == pytest.approx(0.8)
        assert len(agg["outputs"]) == 2

    def test_partial_failure(self):
        """One failure makes all_succeeded=False."""
        strategy = ConcreteStrategy()
        results = [
            AgentResult(agent_id="a", success=True, output={}, confidence=1.0),
            AgentResult(agent_id="b", success=False, output={}, confidence=0.0),
        ]
        agg = strategy._aggregate_results(results)

        assert agg["all_succeeded"] is False
        assert agg["avg_confidence"] == pytest.approx(0.5)

    def test_single_result(self):
        """Single-element list works correctly."""
        strategy = ConcreteStrategy()
        results = [
            AgentResult(agent_id="solo", success=True, output={"k": "v"}, confidence=0.6),
        ]
        agg = strategy._aggregate_results(results)

        assert agg["num_agents"] == 1
        assert agg["avg_confidence"] == pytest.approx(0.6)
