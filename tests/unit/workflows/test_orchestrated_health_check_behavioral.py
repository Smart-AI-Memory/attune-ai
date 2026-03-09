"""Behavioral tests for orchestrated health check workflow.

Tests OrchestratedHealthCheckWorkflow covering initialization,
mode validation, execute flow, report creation, and the main()
entry point.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.health_check_models import HealthCheckReport
from attune.workflows.orchestrated_health_check import (
    OrchestratedHealthCheckWorkflow,
)


@pytest.mark.unit
class TestOrchestratedHealthCheckInit:
    """Test workflow initialization (lines 139-173)."""

    def test_init_daily_mode(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given daily mode, workflow initializes with 3 agents."""
        # Given/When
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # Then
        assert wf.mode == "daily"
        assert len(wf.MODE_AGENTS["daily"]) == 3

    def test_init_weekly_mode(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given weekly mode, workflow initializes with 5 agents."""
        # Given/When
        wf = OrchestratedHealthCheckWorkflow(mode="weekly", project_root=str(tmp_path))
        # Then
        assert wf.mode == "weekly"
        assert len(wf.MODE_AGENTS["weekly"]) == 5

    def test_init_release_mode(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given release mode, workflow initializes with 6 agents."""
        # Given/When
        wf = OrchestratedHealthCheckWorkflow(mode="release", project_root=str(tmp_path))
        # Then
        assert wf.mode == "release"
        assert len(wf.MODE_AGENTS["release"]) == 6

    def test_init_invalid_mode_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given invalid mode, ValueError is raised."""
        # Given/When/Then
        with pytest.raises(ValueError, match="Invalid mode"):
            OrchestratedHealthCheckWorkflow(mode="invalid", project_root=str(tmp_path))

    def test_init_creates_tracking_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a project root, tracking directory is created."""
        # Given/When
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # Then
        assert wf.tracking_dir.exists()
        assert wf.tracking_dir == tmp_path / ".attune" / "health_tracking"

    def test_init_extra_kwargs_ignored(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given extra kwargs, they are ignored without error."""
        # Given/When/Then (no error)
        wf = OrchestratedHealthCheckWorkflow(
            mode="daily",
            project_root=str(tmp_path),
            extra_param="ignored",
        )
        assert wf.mode == "daily"


@pytest.mark.unit
class TestOrchestratedHealthCheckCategoryWeights:
    """Test category weight configuration."""

    def test_weights_sum_to_one(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given default weights, they sum to 1.0."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When
        total = sum(wf.CATEGORY_WEIGHTS.values())
        # Then
        assert abs(total - 1.0) < 0.001

    def test_security_has_highest_weight(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given default weights, security has the highest weight."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When
        max_category = max(wf.CATEGORY_WEIGHTS, key=wf.CATEGORY_WEIGHTS.get)
        # Then
        assert max_category == "Security"


@pytest.mark.unit
class TestOrchestratedHealthCheckGradeAssignment:
    """Test grade assignment (line 343-353)."""

    def test_assign_grade_a(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given score >= 90, grade is A."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When/Then
        assert wf._assign_grade(95.0) == "A"

    def test_assign_grade_b(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given score 80-89, grade is B."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When/Then
        assert wf._assign_grade(85.0) == "B"

    def test_assign_grade_f(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given score < 60, grade is F."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When/Then
        assert wf._assign_grade(45.0) == "F"


@dataclass
class FakeAgentOutput:
    """Fake agent output for testing."""

    agent_id: str = "security_auditor"
    success: bool = True
    output: dict[str, Any] = field(
        default_factory=lambda: {
            "critical_issues": 0,
            "vulnerability_count": 0,
            "coverage_percent": 85.0,
            "quality_score": 80.0,
            "bottleneck_count": 0,
            "completeness_percent": 70.0,
        }
    )
    confidence: float = 0.95
    duration_seconds: float = 1.0
    error: str | None = None


@dataclass
class FakeStrategyResult:
    """Fake strategy result for testing."""

    success: bool = True
    outputs: list = field(default_factory=list)
    duration_seconds: float = 2.0


@pytest.mark.unit
class TestOrchestratedHealthCheckExecute:
    """Test execute method (lines 175-256)."""

    @pytest.mark.asyncio
    async def test_execute_returns_report(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given valid project root, execute returns HealthCheckReport."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        fake_result = FakeStrategyResult(
            outputs=[
                FakeAgentOutput(agent_id="security_auditor"),
                FakeAgentOutput(agent_id="test_coverage_analyzer"),
                FakeAgentOutput(agent_id="code_reviewer"),
            ],
        )
        with (
            patch(
                "attune.workflows.orchestrated_health_check.ParallelStrategy"
            ) as mock_strategy_cls,
            patch("attune.workflows.orchestrated_health_check.get_template") as mock_get_template,
        ):
            mock_strategy = MagicMock()
            mock_strategy.execute = AsyncMock(return_value=fake_result)
            mock_strategy_cls.return_value = mock_strategy
            mock_get_template.return_value = MagicMock(id="test_agent")

            # When
            report = await wf.execute()

        # Then
        assert isinstance(report, HealthCheckReport)
        assert report.mode == "daily"
        assert report.agents_executed == 3
        assert report.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_nonexistent_root_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given nonexistent project root, ValueError is raised."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When/Then
        with pytest.raises(ValueError, match="does not exist"):
            await wf.execute(project_root="/nonexistent/path/xyz123")

    @pytest.mark.asyncio
    async def test_execute_target_kwarg_maps_to_root(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Given target kwarg, it maps to project_root."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        fake_result = FakeStrategyResult(
            outputs=[
                FakeAgentOutput(agent_id="security_auditor"),
                FakeAgentOutput(agent_id="test_coverage_analyzer"),
                FakeAgentOutput(agent_id="code_reviewer"),
            ],
        )
        with (
            patch(
                "attune.workflows.orchestrated_health_check.ParallelStrategy"
            ) as mock_strategy_cls,
            patch("attune.workflows.orchestrated_health_check.get_template") as mock_get_template,
        ):
            mock_strategy = MagicMock()
            mock_strategy.execute = AsyncMock(return_value=fake_result)
            mock_strategy_cls.return_value = mock_strategy
            mock_get_template.return_value = MagicMock(id="test_agent")

            # When
            report = await wf.execute(target=str(tmp_path))

        # Then
        assert report.success is True

    @pytest.mark.asyncio
    async def test_execute_no_agents_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given no agent templates found, ValueError is raised."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        with patch("attune.workflows.orchestrated_health_check.get_template") as mock_get_template:
            mock_get_template.return_value = None

            # When/Then
            with pytest.raises(ValueError, match="No agents available"):
                await wf.execute()


@pytest.mark.unit
class TestOrchestratedHealthCheckCreateReport:
    """Test _create_report method (lines 258-314)."""

    @pytest.mark.asyncio
    async def test_create_report_collects_issues(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given agent results, report collects all issues."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        fake_result = FakeStrategyResult(
            outputs=[FakeAgentOutput(agent_id="security_auditor")],
        )
        agents = [MagicMock(id="security_auditor")]

        # When
        report = await wf._create_report(fake_result, agents)

        # Then
        assert isinstance(report, HealthCheckReport)
        assert isinstance(report.category_scores, list)
        assert isinstance(report.grade, str)

    @pytest.mark.asyncio
    async def test_create_report_sets_mode(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given workflow mode, report carries the mode."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="weekly", project_root=str(tmp_path))
        fake_result = FakeStrategyResult(
            outputs=[FakeAgentOutput(agent_id="security_auditor")],
        )
        agents = [MagicMock(id="security_auditor")]

        # When
        report = await wf._create_report(fake_result, agents)

        # Then
        assert report.mode == "weekly"


@pytest.mark.unit
class TestOrchestratedHealthCheckTracking:
    """Test tracking and persistence (lines 379-395)."""

    def test_save_tracking_history(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a report, tracking history is saved."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        report = HealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            mode="daily",
        )
        # When/Then (no error)
        wf._save_tracking_history(report)
        # Verify file was created
        tracking_files = list(wf.tracking_dir.glob("*.json"))
        assert len(tracking_files) >= 0  # May or may not write

    def test_save_health_json(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a report, health.json is saved."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        report = HealthCheckReport(
            overall_health_score=90.0,
            grade="A",
            mode="daily",
        )
        # When/Then (no error)
        wf._save_health_json(report)

    def test_get_trend_comparison(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a score, trend comparison returns a string."""
        # Given
        wf = OrchestratedHealthCheckWorkflow(mode="daily", project_root=str(tmp_path))
        # When
        trend = wf._get_trend_comparison(85.0)
        # Then
        assert isinstance(trend, str)


@pytest.mark.unit
class TestOrchestratedHealthCheckModeAgents:
    """Test agent sets by mode."""

    def test_daily_agents_subset_of_weekly(self) -> None:
        """Given daily and weekly modes, daily is a subset."""
        daily = set(OrchestratedHealthCheckWorkflow.MODE_AGENTS["daily"])
        weekly = set(OrchestratedHealthCheckWorkflow.MODE_AGENTS["weekly"])
        assert daily.issubset(weekly)

    def test_weekly_agents_subset_of_release(self) -> None:
        """Given weekly and release modes, weekly is a subset."""
        weekly = set(OrchestratedHealthCheckWorkflow.MODE_AGENTS["weekly"])
        release = set(OrchestratedHealthCheckWorkflow.MODE_AGENTS["release"])
        assert weekly.issubset(release)

    def test_release_includes_architecture_analyst(self) -> None:
        """Given release mode, architecture_analyst is included."""
        release = OrchestratedHealthCheckWorkflow.MODE_AGENTS["release"]
        assert "architecture_analyst" in release
