"""Tests for pipeline orchestrator."""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.pipeline.models import PipelineResult
from attune.pipeline.orchestrator import PipelineOrchestrator
from attune.wizards.decomposer import DecomposedTask


def _make_task(
    task_id: str = "1",
    name: str = "test-task",
    files_to_create: list | None = None,
    files_to_modify: list | None = None,
) -> DecomposedTask:
    """Create a test DecomposedTask."""
    return DecomposedTask(
        task_id=task_id,
        name=name,
        objective="Test objective",
        files_to_create=files_to_create
        or [{"path": "src/attune/foo.py", "description": "New file"}],
        files_to_modify=files_to_modify or [],
        validation_checks=["check1"],
        risks=[],
        dependencies=[],
    )


class TestPipelineOrchestratorInit:
    """Tests for orchestrator initialization."""

    def test_reads_spec_on_init(self):
        """Orchestrator reads tasks from spec on init."""
        orch = PipelineOrchestrator(".claude/plans/pipeline-orchestrator.md")
        assert len(orch.tasks) == 5
        assert orch.spec_path == ".claude/plans/pipeline-orchestrator.md"

    def test_skip_flags_default_false(self):
        """Skip flags default to False."""
        orch = PipelineOrchestrator(".claude/plans/pipeline-orchestrator.md")
        assert not orch.skip_gates
        assert not orch.skip_tests
        assert not orch.skip_simplify

    def test_skip_flags_settable(self):
        """Skip flags can be set."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=True,
        )
        assert orch.skip_gates
        assert orch.skip_tests
        assert orch.skip_simplify


class TestRunGatesForTask:
    """Tests for run_gates_for_task."""

    @pytest.mark.asyncio
    async def test_all_skipped_returns_executed(self):
        """With all gates skipped, task is just marked executed."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()
        result = await orch.run_gates_for_task(task)

        assert result.executed
        assert result.quality_gate_passed is None
        assert result.tests_passed is None
        assert not result.simplified

    @pytest.mark.asyncio
    async def test_gate_failure_stops_early(self):
        """Failed quality gate prevents tests and simplify."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.quality_gate_results = {"min_quality": False}
        mock_result.agent_results = []
        mock_result.total_cost = 0.01
        mock_result.execution_time_ms = 100

        with patch("attune.pipeline.orchestrator.DynamicTeamBuilder") as mock_builder_cls:
            mock_team = AsyncMock()
            mock_team.execute.return_value = mock_result
            mock_builder_cls.return_value.build_from_plan.return_value = mock_team

            result = await orch.run_gates_for_task(task)

        assert result.executed
        assert result.quality_gate_passed is False
        assert result.tests_passed is None

    @pytest.mark.asyncio
    async def test_gate_success(self):
        """Successful quality gate records details."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_gate_results = {
            "min_quality": True,
            "min_security": True,
        }
        mock_result.agent_results = [MagicMock(), MagicMock()]
        mock_result.total_cost = 0.05
        mock_result.execution_time_ms = 2000

        with patch("attune.pipeline.orchestrator.DynamicTeamBuilder") as mock_builder_cls:
            mock_team = AsyncMock()
            mock_team.execute.return_value = mock_result
            mock_builder_cls.return_value.build_from_plan.return_value = mock_team

            result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed
        assert result.gate_details["team_success"]
        assert result.cost == 0.05

    @pytest.mark.asyncio
    async def test_gate_exception_fails_gracefully(self):
        """Exception in quality gate marks task as failed."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        with patch(
            "attune.pipeline.orchestrator.DynamicTeamBuilder",
            side_effect=RuntimeError("team build failed"),
        ):
            result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed is False
        assert "Gate error" in result.error


class TestRunTests:
    """Tests for _run_tests and _find_test_files."""

    def test_find_test_files_maps_source(self):
        """Source files are mapped to test paths when they exist."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        # Use a real file path that exists in this project
        task = _make_task(
            files_to_create=[{"path": "src/attune/pipeline/models.py", "description": ""}]
        )
        files = orch._find_test_files(task)
        # tests/unit/pipeline/test_models.py exists, so it should be found
        assert any("test_models.py" in f for f in files)

    def test_find_test_files_includes_test_files(self):
        """Files already named test_* are included directly."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        task = _make_task(files_to_create=[{"path": "tests/unit/test_foo.py", "description": ""}])
        files = orch._find_test_files(task)
        assert "tests/unit/test_foo.py" in files

    def test_run_tests_success(self):
        """_run_tests returns True on success."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        with patch("attune.pipeline.orchestrator.subprocess") as mock_sub:
            mock_sub.run.return_value.returncode = 0
            assert orch._run_tests(["tests/test_x.py"])

    def test_run_tests_failure(self):
        """_run_tests returns False on failure."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        with patch("attune.pipeline.orchestrator.subprocess") as mock_sub:
            mock_sub.run.return_value.returncode = 1
            mock_sub.run.return_value.stdout = "FAILED"
            assert not orch._run_tests(["tests/test_x.py"])

    def test_run_tests_timeout(self):
        """_run_tests returns False on timeout."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=300),
        ):
            assert not orch._run_tests(["tests/test_x.py"])


class TestGetSourceFiles:
    """Tests for _get_source_files."""

    def test_filters_test_files(self):
        """Test files are excluded from source files."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        task = _make_task(
            files_to_create=[
                {"path": "src/attune/foo.py", "description": ""},
                {"path": "tests/unit/test_foo.py", "description": ""},
            ]
        )
        files = orch._get_source_files(task)
        assert "src/attune/foo.py" in files
        assert "tests/unit/test_foo.py" not in files

    def test_filters_non_python(self):
        """Non-Python files are excluded."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
        )
        task = _make_task(
            files_to_create=[
                {"path": "src/attune/foo.py", "description": ""},
                {"path": "docs/readme.md", "description": ""},
            ]
        )
        files = orch._get_source_files(task)
        assert "src/attune/foo.py" in files
        assert "docs/readme.md" not in files


class TestRunSimplify:
    """Tests for _run_simplify path."""

    @pytest.mark.asyncio
    async def test_simplify_runs_when_enabled(self):
        """Simplify path runs when skip_simplify=False."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=False,
        )
        task = _make_task()

        with patch("attune.workflows.simplify_code.SimplifyCodeWorkflow") as mock_simplify_cls:
            mock_wf = AsyncMock()
            mock_simplify_cls.return_value = mock_wf

            result = await orch.run_gates_for_task(task)

        assert result.executed
        assert result.simplified

    @pytest.mark.asyncio
    async def test_simplify_per_file_failure_is_non_fatal(self):
        """Per-file simplify failure is caught internally; pipeline continues."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=False,
        )
        task = _make_task()

        with patch(
            "attune.workflows.simplify_code.SimplifyCodeWorkflow",
            side_effect=RuntimeError("simplify broke"),
        ):
            result = await orch.run_gates_for_task(task)

        # Per-file errors are caught inside _run_simplify, so
        # the outer call succeeds and simplified is set to True
        assert result.executed
        assert result.simplified


class TestRunAll:
    """Tests for run_all."""

    @pytest.mark.asyncio
    async def test_run_all_skipped(self):
        """run_all with all gates skipped processes all tasks."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=True,
        )
        result = await orch.run_all()

        assert isinstance(result, PipelineResult)
        assert len(result.tasks) == 5
        assert all(t.executed for t in result.tasks)
        assert result.success

    @pytest.mark.asyncio
    async def test_run_all_stops_on_gate_failure(self):
        """run_all stops when a quality gate fails."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.quality_gate_results = {"min_quality": False}
        mock_result.agent_results = []
        mock_result.total_cost = 0.01
        mock_result.execution_time_ms = 100

        with patch("attune.pipeline.orchestrator.DynamicTeamBuilder") as mock_builder_cls:
            mock_team = AsyncMock()
            mock_team.execute.return_value = mock_result
            mock_builder_cls.return_value.build_from_plan.return_value = mock_team

            result = await orch.run_all()

        # Should stop after first task fails
        assert len(result.tasks) == 1
        assert not result.success
