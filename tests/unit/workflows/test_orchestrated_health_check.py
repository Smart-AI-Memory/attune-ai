"""Tests for Orchestrated Health Check Workflow

Tests comprehensive health check functionality including:
- All 3 modes (daily, weekly, release)
- Health score calculation
- Grade assignment
- Trend tracking
- Recommendations generation
- CLI integration

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from attune.orchestration.execution_strategies import AgentResult, StrategyResult
from attune.workflows.health_check_scoring import (
    calculate_category_scores,
    calculate_overall_score,
    generate_recommendations,
)
from attune.workflows.orchestrated_health_check import (
    CategoryScore,
    HealthCheckReport,
    OrchestratedHealthCheckWorkflow,
)


class TestCategoryScore:
    """Tests for CategoryScore dataclass."""

    def test_category_score_creation(self):
        """Test creating a category score."""
        score = CategoryScore(
            name="Security",
            score=85.0,
            weight=0.30,
            raw_metrics={"critical": 0, "high": 1},
            issues=["1 high severity issue"],
            passed=True,
        )

        assert score.name == "Security"
        assert score.score == 85.0
        assert score.weight == 0.30
        assert score.passed is True
        assert len(score.issues) == 1

    def test_category_score_defaults(self):
        """Test category score with defaults."""
        score = CategoryScore(name="Coverage", score=75.0, weight=0.25)

        assert score.raw_metrics == {}
        assert score.issues == []
        assert score.passed is True


class TestHealthCheckReport:
    """Tests for HealthCheckReport dataclass."""

    def test_report_creation(self):
        """Test creating a health check report."""
        category_scores = [
            CategoryScore(name="Security", score=90.0, weight=0.30),
            CategoryScore(name="Coverage", score=85.0, weight=0.25),
        ]

        report = HealthCheckReport(
            overall_health_score=87.5,
            grade="B",
            category_scores=category_scores,
            issues=["Minor issue"],
            recommendations=["Fix minor issue"],
            trend="Improving (+2.5 from 85.0)",
            execution_time=5.2,
            mode="weekly",
            agents_executed=5,
        )

        assert report.overall_health_score == 87.5
        assert report.grade == "B"
        assert len(report.category_scores) == 2
        assert report.mode == "weekly"
        assert report.success is True

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        category_scores = [
            CategoryScore(
                name="Security",
                score=90.0,
                weight=0.30,
                raw_metrics={"critical": 0},
                issues=[],
                passed=True,
            ),
        ]

        report = HealthCheckReport(
            overall_health_score=90.0,
            grade="A",
            category_scores=category_scores,
            mode="daily",
        )

        result = report.to_dict()

        assert isinstance(result, dict)
        assert result["overall_health_score"] == 90.0
        assert result["grade"] == "A"
        assert result["mode"] == "daily"
        assert len(result["category_scores"]) == 1
        assert result["category_scores"][0]["name"] == "Security"

    def test_report_format_console_output(self):
        """Test formatting report for console."""
        category_scores = [
            CategoryScore(name="Security", score=95.0, weight=0.30, passed=True),
            CategoryScore(name="Coverage", score=85.0, weight=0.25, passed=True),
        ]

        report = HealthCheckReport(
            overall_health_score=91.0,
            grade="A",
            category_scores=category_scores,
            issues=[],
            recommendations=["Keep up the good work"],
            trend="Stable (~91.0)",
            mode="daily",
            agents_executed=3,
        )

        output = report.format_console_output()

        assert "PROJECT HEALTH CHECK REPORT" in output
        assert "91.0/100" in output
        assert "Grade A" in output
        assert "🏆" in output  # A grade emoji
        assert "Security" in output
        assert "Coverage" in output
        assert "Keep up the good work" in output


class TestOrchestratedHealthCheckWorkflow:
    """Tests for OrchestratedHealthCheckWorkflow."""

    def test_init_valid_mode(self):
        """Test initialization with valid mode."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=".")

        assert workflow.mode == "daily"
        assert workflow.project_root == Path().resolve()
        assert workflow.tracking_dir.exists()

    def test_init_invalid_mode(self):
        """Test initialization with invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            OrchestratedHealthCheckWorkflow(mode="invalid")

    def test_mode_agents_configuration(self):
        """Test agent configuration for each mode."""
        assert len(OrchestratedHealthCheckWorkflow.MODE_AGENTS["daily"]) == 3
        assert len(OrchestratedHealthCheckWorkflow.MODE_AGENTS["weekly"]) == 5
        assert len(OrchestratedHealthCheckWorkflow.MODE_AGENTS["release"]) == 6

        # Daily mode uses basic agents
        assert "security_auditor" in OrchestratedHealthCheckWorkflow.MODE_AGENTS["daily"]
        assert "test_coverage_analyzer" in OrchestratedHealthCheckWorkflow.MODE_AGENTS["daily"]

        # Weekly adds performance and docs
        assert "performance_optimizer" in OrchestratedHealthCheckWorkflow.MODE_AGENTS["weekly"]
        assert "documentation_writer" in OrchestratedHealthCheckWorkflow.MODE_AGENTS["weekly"]

        # Release adds architecture
        assert "architecture_analyst" in OrchestratedHealthCheckWorkflow.MODE_AGENTS["release"]

    def test_category_weights_sum_to_one(self):
        """Test category weights sum to 1.0."""
        weights = OrchestratedHealthCheckWorkflow.CATEGORY_WEIGHTS
        total_weight = sum(weights.values())

        assert abs(total_weight - 1.0) < 0.01

    def test_grade_thresholds(self):
        """Test grade threshold configuration."""
        thresholds = OrchestratedHealthCheckWorkflow.GRADE_THRESHOLDS

        assert thresholds["A"] == 90.0
        assert thresholds["B"] == 80.0
        assert thresholds["C"] == 70.0
        assert thresholds["D"] == 60.0

    @pytest.mark.asyncio
    async def test_execute_daily_mode(self, tmp_path):
        """Test executing health check in daily mode."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        # Mock the strategy execution
        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            # Create mock agent results
            mock_results = [
                AgentResult(
                    agent_id="security_auditor",
                    success=True,
                    output={
                        "critical_issues": 0,
                        "high_issues": 0,
                        "medium_issues": 1,
                    },
                    confidence=0.9,
                    duration_seconds=1.0,
                ),
                AgentResult(
                    agent_id="test_coverage_analyzer",
                    success=True,
                    output={"coverage_percent": 85.0},
                    confidence=0.85,
                    duration_seconds=1.2,
                ),
                AgentResult(
                    agent_id="code_reviewer",
                    success=True,
                    output={"quality_score": 8.0},
                    confidence=0.88,
                    duration_seconds=1.5,
                ),
            ]

            mock_strategy_result = StrategyResult(
                success=True,
                outputs=mock_results,
                aggregated_output={},
                total_duration=3.7,
            )

            mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

            # Execute workflow
            report = await workflow.execute()

            # Assertions
            assert report.success is True
            assert report.mode == "daily"
            assert report.agents_executed == 3
            assert report.overall_health_score > 0
            assert report.grade in ["A", "B", "C", "D", "F"]
            assert len(report.category_scores) == 3  # Security, Coverage, Quality

    @pytest.mark.asyncio
    async def test_execute_weekly_mode(self, tmp_path):
        """Test executing health check in weekly mode."""
        workflow = OrchestratedHealthCheckWorkflow(mode="weekly", project_root=str(tmp_path))

        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            mock_results = [
                AgentResult(
                    agent_id="security_auditor",
                    success=True,
                    output={"critical_issues": 0, "high_issues": 0, "medium_issues": 0},
                    confidence=0.95,
                    duration_seconds=1.0,
                ),
                AgentResult(
                    agent_id="test_coverage_analyzer",
                    success=True,
                    output={"coverage_percent": 90.0},
                    confidence=0.9,
                    duration_seconds=1.0,
                ),
                AgentResult(
                    agent_id="code_reviewer",
                    success=True,
                    output={"quality_score": 9.0},
                    confidence=0.92,
                    duration_seconds=1.0,
                ),
                AgentResult(
                    agent_id="performance_optimizer",
                    success=True,
                    output={"bottleneck_count": 1},
                    confidence=0.85,
                    duration_seconds=1.0,
                ),
                AgentResult(
                    agent_id="documentation_writer",
                    success=True,
                    output={"coverage_percent": 95.0},
                    confidence=0.88,
                    duration_seconds=1.0,
                ),
            ]

            mock_strategy_result = StrategyResult(
                success=True,
                outputs=mock_results,
                aggregated_output={},
                total_duration=5.0,
            )

            mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

            report = await workflow.execute()

            assert report.success is True
            assert report.mode == "weekly"
            assert report.agents_executed == 5
            assert len(report.category_scores) == 5  # All categories

    @pytest.mark.asyncio
    async def test_execute_release_mode(self, tmp_path):
        """Test executing health check in release mode."""
        workflow = OrchestratedHealthCheckWorkflow(mode="release", project_root=str(tmp_path))

        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            mock_results = [
                AgentResult(
                    agent_id="security_auditor",
                    success=True,
                    output={"critical_issues": 0, "high_issues": 0, "medium_issues": 0},
                    confidence=0.95,
                    duration_seconds=2.0,
                ),
                AgentResult(
                    agent_id="test_coverage_analyzer",
                    success=True,
                    output={"coverage_percent": 92.0},
                    confidence=0.92,
                    duration_seconds=2.0,
                ),
                AgentResult(
                    agent_id="code_reviewer",
                    success=True,
                    output={"quality_score": 9.5},
                    confidence=0.95,
                    duration_seconds=2.0,
                ),
                AgentResult(
                    agent_id="performance_optimizer",
                    success=True,
                    output={"bottleneck_count": 0},
                    confidence=0.9,
                    duration_seconds=2.0,
                ),
                AgentResult(
                    agent_id="documentation_writer",
                    success=True,
                    output={"coverage_percent": 100.0},
                    confidence=0.95,
                    duration_seconds=2.0,
                ),
                AgentResult(
                    agent_id="architecture_analyst",
                    success=True,
                    output={"quality_score": 9.0},
                    confidence=0.9,
                    duration_seconds=2.0,
                ),
            ]

            mock_strategy_result = StrategyResult(
                success=True,
                outputs=mock_results,
                aggregated_output={},
                total_duration=12.0,
            )

            mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

            report = await workflow.execute()

            assert report.success is True
            assert report.mode == "release"
            assert report.agents_executed == 6

    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        category_scores = [
            CategoryScore(name="Security", score=100.0, weight=0.30),
            CategoryScore(name="Coverage", score=80.0, weight=0.25),
            CategoryScore(name="Quality", score=90.0, weight=0.20),
            CategoryScore(name="Performance", score=85.0, weight=0.15),
            CategoryScore(name="Documentation", score=95.0, weight=0.10),
        ]

        # Expected: (100*0.3 + 80*0.25 + 90*0.2 + 85*0.15 + 95*0.1) / (0.3+0.25+0.2+0.15+0.1)
        # = (30 + 20 + 18 + 12.75 + 9.5) / 1.0 = 90.25
        overall = workflow._calculate_overall_score(category_scores)

        assert abs(overall - 90.25) < 0.1

    def test_assign_grade(self):
        """Test grade assignment based on score."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        assert workflow._assign_grade(95.0) == "A"
        assert workflow._assign_grade(85.0) == "B"
        assert workflow._assign_grade(75.0) == "C"
        assert workflow._assign_grade(65.0) == "D"
        assert workflow._assign_grade(55.0) == "F"

    def test_generate_recommendations_all_passed(self):
        """Test recommendations when all categories pass."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        category_scores = [
            CategoryScore(name="Security", score=95.0, weight=0.30, passed=True),
            CategoryScore(name="Coverage", score=85.0, weight=0.25, passed=True),
            CategoryScore(name="Quality", score=90.0, weight=0.20, passed=True),
        ]

        recommendations = workflow._generate_recommendations(category_scores)

        assert len(recommendations) > 0
        assert any("good" in rec.lower() for rec in recommendations)

    def test_generate_recommendations_failures(self):
        """Test recommendations with failing categories."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        category_scores = [
            CategoryScore(
                name="Security",
                score=70.0,
                weight=0.30,
                passed=False,
                issues=["2 critical issues"],
            ),
            CategoryScore(
                name="Coverage",
                score=60.0,
                weight=0.25,
                passed=False,
                raw_metrics={"coverage_percent": 60.0},
            ),
            CategoryScore(
                name="Quality",
                score=50.0,
                weight=0.20,
                passed=False,
                raw_metrics={"quality_score": 5.0},
            ),
        ]

        recommendations = workflow._generate_recommendations(category_scores)

        assert len(recommendations) >= 3
        assert any("security" in rec.lower() for rec in recommendations)
        assert any("coverage" in rec.lower() for rec in recommendations)
        assert any("quality" in rec.lower() for rec in recommendations)

    def test_trend_tracking_no_history(self, tmp_path):
        """Test trend tracking with no history."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        trend = workflow._get_trend_comparison(85.0)

        assert "No historical data" in trend

    def test_trend_tracking_first_baseline(self, tmp_path):
        """Test trend tracking establishing first baseline."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        # Create history file with one entry
        history_file = workflow.tracking_dir / "history.jsonl"
        history_file.write_text(
            json.dumps({"timestamp": "2025-01-01", "overall_health_score": 80.0}) + "\n",
        )

        trend = workflow._get_trend_comparison(85.0)

        assert "baseline" in trend.lower()

    def test_trend_tracking_improving(self, tmp_path):
        """Test trend tracking with improving score."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        # Create history with two entries
        # Note: _get_trend_comparison reads lines[-2] which is the second-to-last
        history_file = workflow.tracking_dir / "history.jsonl"
        with history_file.open("w") as f:
            f.write(json.dumps({"timestamp": "2025-01-01", "overall_health_score": 70.0}) + "\n")
            f.write(json.dumps({"timestamp": "2025-01-02", "overall_health_score": 75.0}) + "\n")

        trend = workflow._get_trend_comparison(85.0)

        assert "Improving" in trend
        # Compares 85.0 vs lines[-2] which is the first entry (70.0)
        assert "+15.0" in trend

    def test_trend_tracking_declining(self, tmp_path):
        """Test trend tracking with declining score."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        history_file = workflow.tracking_dir / "history.jsonl"
        with history_file.open("w") as f:
            f.write(json.dumps({"timestamp": "2025-01-01", "overall_health_score": 95.0}) + "\n")
            f.write(json.dumps({"timestamp": "2025-01-02", "overall_health_score": 90.0}) + "\n")

        trend = workflow._get_trend_comparison(80.0)

        assert "Declining" in trend
        # Compares 80.0 vs lines[-2] which is the first entry (95.0)
        assert "-15.0" in trend

    def test_trend_tracking_stable(self, tmp_path):
        """Test trend tracking with stable score."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        history_file = workflow.tracking_dir / "history.jsonl"
        with history_file.open("w") as f:
            f.write(json.dumps({"timestamp": "2025-01-01", "overall_health_score": 85.0}) + "\n")
            f.write(json.dumps({"timestamp": "2025-01-02", "overall_health_score": 85.5}) + "\n")

        trend = workflow._get_trend_comparison(85.3)

        assert "Stable" in trend

    def test_save_tracking_history(self, tmp_path):
        """Test saving tracking history."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        report = HealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            category_scores=[
                CategoryScore(name="Security", score=90.0, weight=0.30),
                CategoryScore(name="Coverage", score=85.0, weight=0.25),
            ],
            mode="daily",
            agents_executed=3,
        )

        workflow._save_tracking_history(report)

        # Verify file was created
        history_file = workflow.tracking_dir / "history.jsonl"
        assert history_file.exists()

        # Verify content
        with history_file.open("r") as f:
            entry = json.loads(f.read())
            assert entry["overall_health_score"] == 85.0
            assert entry["grade"] == "B"
            assert entry["mode"] == "daily"

    def test_calculate_category_scores_security_critical(self):
        """Test security category with critical issues."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        agent_results = {
            "security_auditor": {
                "output": {"critical_issues": 2, "high_issues": 1, "medium_issues": 3},
            },
        }

        scores = workflow._calculate_category_scores(agent_results)

        security_score = next(s for s in scores if s.name == "Security")
        # 100 - (2*20) - (1*10) - (3*5) = 100 - 40 - 10 - 15 = 35
        assert security_score.score == 35.0
        assert not security_score.passed
        assert len(security_score.issues) > 0

    def test_calculate_category_scores_perfect_security(self):
        """Test security category with no issues."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        agent_results = {
            "security_auditor": {
                "output": {"critical_issues": 0, "high_issues": 0, "medium_issues": 0},
            },
        }

        scores = workflow._calculate_category_scores(agent_results)

        security_score = next(s for s in scores if s.name == "Security")
        assert security_score.score == 100.0
        assert security_score.passed
        assert len(security_score.issues) == 0

    def test_calculate_category_scores_coverage(self):
        """Test coverage category score calculation."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        agent_results = {"test_coverage_analyzer": {"output": {"coverage_percent": 75.0}}}

        scores = workflow._calculate_category_scores(agent_results)

        coverage_score = next(s for s in scores if s.name == "Coverage")
        assert coverage_score.score == 75.0
        assert not coverage_score.passed  # Below 80%
        assert len(coverage_score.issues) > 0

    def test_calculate_category_scores_quality(self):
        """Test quality category score calculation."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily")

        agent_results = {"code_reviewer": {"output": {"quality_score": 8.5}}}

        scores = workflow._calculate_category_scores(agent_results)

        quality_score = next(s for s in scores if s.name == "Quality")
        assert quality_score.score == 85.0  # 8.5 * 10
        assert quality_score.passed
        assert len(quality_score.issues) == 0

    def test_calculate_category_scores_performance(self):
        """Test performance category score calculation."""
        workflow = OrchestratedHealthCheckWorkflow(mode="weekly")

        agent_results = {"performance_optimizer": {"output": {"bottleneck_count": 3}}}

        scores = workflow._calculate_category_scores(agent_results)

        perf_score = next(s for s in scores if s.name == "Performance")
        assert perf_score.score == 70.0  # 100 - (3 * 10)
        assert not perf_score.passed  # > 2 bottlenecks

    def test_calculate_category_scores_documentation(self):
        """Test documentation category score calculation."""
        workflow = OrchestratedHealthCheckWorkflow(mode="weekly")

        agent_results = {"documentation_writer": {"output": {"coverage_percent": 88.0}}}

        scores = workflow._calculate_category_scores(agent_results)

        docs_score = next(s for s in scores if s.name == "Documentation")
        assert docs_score.score == 88.0
        assert not docs_score.passed  # < 90%
        assert len(docs_score.issues) > 0


@pytest.mark.asyncio
async def test_health_check_integration(tmp_path):
    """Integration test for complete health check workflow."""
    workflow = OrchestratedHealthCheckWorkflow(mode="weekly", project_root=str(tmp_path))

    with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
        # Create comprehensive mock results
        mock_results = [
            AgentResult(
                agent_id="security_auditor",
                success=True,
                output={"critical_issues": 0, "high_issues": 1, "medium_issues": 2},
                confidence=0.9,
                duration_seconds=1.5,
            ),
            AgentResult(
                agent_id="test_coverage_analyzer",
                success=True,
                output={"coverage_percent": 82.5},
                confidence=0.88,
                duration_seconds=1.2,
            ),
            AgentResult(
                agent_id="code_reviewer",
                success=True,
                output={"quality_score": 7.8},
                confidence=0.85,
                duration_seconds=1.8,
            ),
            AgentResult(
                agent_id="performance_optimizer",
                success=True,
                output={"bottleneck_count": 2},
                confidence=0.82,
                duration_seconds=2.0,
            ),
            AgentResult(
                agent_id="documentation_writer",
                success=True,
                output={"coverage_percent": 92.0},
                confidence=0.9,
                duration_seconds=1.0,
            ),
        ]

        mock_strategy_result = StrategyResult(
            success=True,
            outputs=mock_results,
            aggregated_output={},
            total_duration=7.5,
        )

        mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

        # Execute workflow
        report = await workflow.execute()

        # Comprehensive assertions
        assert report.success is True
        assert report.mode == "weekly"
        assert report.agents_executed == 5
        assert 70.0 <= report.overall_health_score <= 90.0
        assert report.grade in ["A", "B", "C"]
        assert len(report.category_scores) == 5
        assert len(report.recommendations) > 0
        assert report.execution_time >= 0  # May be 0.0 with fast mocks on Windows

        # Verify tracking history was saved
        history_file = workflow.tracking_dir / "history.jsonl"
        assert history_file.exists()

        # Verify console output formatting
        output = report.format_console_output()
        assert "PROJECT HEALTH CHECK REPORT" in output
        # Format shows one decimal place (e.g., "81.4")
        assert f"{report.overall_health_score:.1f}" in output
        assert report.grade in output


class TestExecutePathKwarg:
    """Tests for the `path=` kwarg migration in `execute()`.

    PR-1 of workflow-path-arg-unification (2026-05-13) renames the
    `project_root=` kwarg on `execute()` to `path=`, keeping the
    legacy name as a deprecated alias for one major version.
    """

    @pytest.fixture
    def _mock_strategy(self):
        """Patch ParallelStrategy so execute() returns quickly."""
        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            mock_result = StrategyResult(
                success=True,
                outputs=[
                    AgentResult(
                        agent_id="security_auditor",
                        success=True,
                        output={"critical_issues": 0, "high_issues": 0, "medium_issues": 0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                    AgentResult(
                        agent_id="test_coverage_analyzer",
                        success=True,
                        output={"coverage_percent": 80.0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                    AgentResult(
                        agent_id="code_reviewer",
                        success=True,
                        output={"quality_score": 8.0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                ],
                aggregated_output={},
                total_duration=0.3,
            )
            mock_strategy.return_value.execute = AsyncMock(return_value=mock_result)
            yield mock_strategy

    @pytest.mark.asyncio
    async def test_execute_accepts_path_kwarg(self, tmp_path, _mock_strategy):
        """execute(path=...) overrides self.project_root."""
        other_root = tmp_path / "other"
        other_root.mkdir()
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        await workflow.execute(path=str(other_root))

        assert workflow.project_root == other_root.resolve()

    @pytest.mark.asyncio
    async def test_execute_legacy_project_root_warns(self, tmp_path, _mock_strategy):
        """execute(project_root=...) emits DeprecationWarning AND still runs."""
        other_root = tmp_path / "other"
        other_root.mkdir()
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        with pytest.warns(DeprecationWarning, match="project_root"):
            report = await workflow.execute(project_root=str(other_root))

        assert workflow.project_root == other_root.resolve()
        assert report.success is True

    @pytest.mark.asyncio
    async def test_execute_both_kwargs_path_wins(self, tmp_path, _mock_strategy):
        """execute(path=A, project_root=B) uses A and warns about the conflict."""
        path_root = tmp_path / "via_path"
        path_root.mkdir()
        legacy_root = tmp_path / "via_legacy"
        legacy_root.mkdir()
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        with pytest.warns(DeprecationWarning, match="both"):
            await workflow.execute(path=str(path_root), project_root=str(legacy_root))

        assert workflow.project_root == path_root.resolve()

    @pytest.mark.asyncio
    async def test_target_still_maps_to_path(self, tmp_path, _mock_strategy):
        """The VSCode-compat target= kwarg still routes to path."""
        other_root = tmp_path / "via_target"
        other_root.mkdir()
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        await workflow.execute(target=str(other_root))

        assert workflow.project_root == other_root.resolve()


class TestUnmeasuredCategories:
    """Regression pins for roundtable q-workflow-fleet-health-001 (Sev2).

    A metric that was not measured must not be a number: categories whose
    agent produced no measurement are N/A (measured=False), excluded from
    the weighted score, and the report says so — never default-to-perfect.
    """

    def test_missing_agents_yield_unmeasured_categories(self):
        """No agent results → every category is unmeasured, none perfect."""
        scores = calculate_category_scores({})

        assert len(scores) == 3  # Security, Coverage, Quality
        assert all(s.measured is False for s in scores)
        assert all(s.passed is False for s in scores)
        security = next(s for s in scores if s.name == "Security")
        assert security.score != 100.0
        assert any("not measured" in issue for issue in security.issues)

    def test_failed_agent_error_output_is_unmeasured(self):
        """The error-shaped output a crashed agent emits is not a measurement."""
        agent_results = {
            "security_auditor": {
                "success": False,
                "output": {"agent_role": "sec", "error_details": "boom"},
            },
            "test_coverage_analyzer": {
                "success": False,
                "output": {"agent_role": "cov", "error_details": "no coverage.json"},
            },
            "code_reviewer": {"success": False, "output": {}},
        }

        scores = calculate_category_scores(agent_results)

        assert all(s.measured is False for s in scores)

    def test_unmeasured_categories_excluded_from_overall_score(self):
        """The weighted score covers measured categories only — no dilution."""
        agent_results = {
            "security_auditor": {
                "output": {"critical_issues": 1, "high_issues": 0, "medium_issues": 0},
            },
        }

        scores = calculate_category_scores(agent_results)
        security = next(s for s in scores if s.name == "Security")
        assert security.measured is True
        assert security.score == 80.0

        # Coverage and Quality are unmeasured; only Security's 80 counts
        assert calculate_overall_score(scores) == 80.0

    def test_overall_score_zero_when_nothing_measured(self):
        """With no measurements at all the score is 0.0, never a fabricated value."""
        assert calculate_overall_score(calculate_category_scores({})) == 0.0

    def test_recommendations_report_missing_data_not_fake_failures(self):
        """Unmeasured categories surface as missing data, not 0.0% failures."""
        recommendations = generate_recommendations(calculate_category_scores({}))
        joined = "\n".join(recommendations)

        assert "Not measured" in joined
        assert "Security" in joined
        # No fabricated numbers and no all-clear on zero data
        assert "currently 0.0" not in joined
        assert "health looks good" not in joined

    def test_report_renders_na_and_degraded(self):
        """Console output shows N/A rows and the DEGRADED banner."""
        report = HealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            category_scores=[
                CategoryScore(name="Coverage", score=85.0, weight=0.25),
                CategoryScore(
                    name="Security",
                    score=0.0,
                    weight=0.30,
                    passed=False,
                    measured=False,
                    issues=["Security not measured — security_auditor produced no measurement"],
                ),
            ],
            degraded=True,
        )

        output = report.format_console_output()

        assert "DEGRADED" in output
        assert "N/A (not measured)" in output
        assert "85.0/100" in output  # the measured part still renders

    def test_report_all_unmeasured_renders_na_not_a_number(self):
        """Grade N/A: the header never prints a numeric overall score."""
        report = HealthCheckReport(
            overall_health_score=0.0,
            grade="N/A",
            category_scores=[
                CategoryScore(
                    name="Security", score=0.0, weight=0.30, passed=False, measured=False
                ),
            ],
            degraded=True,
        )

        output = report.format_console_output()

        assert "N/A — no categories were measured" in output
        assert "0.0/100" not in output

    def test_to_dict_carries_measured_and_degraded(self):
        """Serialized reports expose the degraded flag and per-category measured."""
        report = HealthCheckReport(
            overall_health_score=0.0,
            grade="N/A",
            category_scores=[
                CategoryScore(
                    name="Security", score=0.0, weight=0.30, passed=False, measured=False
                ),
            ],
            degraded=True,
        )

        data = report.to_dict()

        assert data["degraded"] is True
        assert data["category_scores"][0]["measured"] is False

    @pytest.mark.asyncio
    async def test_execute_all_agents_failed_reports_degraded_na(self, tmp_path):
        """End-to-end: an all-agents-failed run is DEGRADED grade N/A, not 100/A."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            mock_results = [
                AgentResult(
                    agent_id=agent_id,
                    success=False,
                    output={"agent_role": agent_id, "error_details": "crashed"},
                    error="crashed",
                    confidence=0.0,
                    duration_seconds=0.1,
                )
                for agent_id in ("security_auditor", "test_coverage_analyzer", "code_reviewer")
            ]
            mock_strategy_result = StrategyResult(
                success=False,
                outputs=mock_results,
                aggregated_output={},
                total_duration=0.3,
            )
            mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

            report = await workflow.execute()

        assert report.degraded is True
        assert report.grade == "N/A"
        assert report.overall_health_score == 0.0
        output = report.format_console_output()
        assert "DEGRADED" in output
        assert "100.0/100" not in output

    @pytest.mark.asyncio
    async def test_execute_partial_measurement_is_degraded_but_scored(self, tmp_path):
        """One measured category scores; the missing ones mark the run degraded."""
        workflow = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))

        with patch("attune.workflows.orchestrated_health_check.ParallelStrategy") as mock_strategy:
            mock_results = [
                AgentResult(
                    agent_id="test_coverage_analyzer",
                    success=True,
                    output={"coverage_percent": 85.0},
                    confidence=0.85,
                    duration_seconds=1.0,
                ),
            ]
            mock_strategy_result = StrategyResult(
                success=True,
                outputs=mock_results,
                aggregated_output={},
                total_duration=1.0,
            )
            mock_strategy.return_value.execute = AsyncMock(return_value=mock_strategy_result)

            report = await workflow.execute()

        assert report.degraded is True
        assert report.overall_health_score == 85.0  # coverage only, undiluted
        assert report.grade == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
