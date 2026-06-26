"""Tests for pipeline orchestrator."""

import subprocess
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.pipeline.models import PipelineResult
from attune.pipeline.orchestrator import PipelineOrchestrator
from attune.wizards.decomposer import DecomposedTask


@pytest.fixture(autouse=True)
def _mock_read_spec():
    """Patch read_spec so tests don't need the local plan file."""
    tasks = [
        DecomposedTask(
            task_id=str(i),
            name=f"task-{i}",
            objective="Test objective",
            files_to_create=[{"path": f"src/attune/t{i}.py", "description": "f"}],
            files_to_modify=[],
            validation_checks=["check"],
            risks=[],
            dependencies=[],
        )
        for i in range(1, 6)
    ]
    with patch("attune.pipeline.orchestrator.read_spec", return_value=tasks):
        yield


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
        files_to_create=(
            [{"path": "src/attune/foo.py", "description": "New file"}]
            if files_to_create is None
            else files_to_create
        ),
        files_to_modify=files_to_modify or [],
        validation_checks=["check1"],
        risks=[],
        dependencies=[],
    )


def _fake_review_result(score, *, success=True, cost=0.01):
    """Build a fake review WorkflowResult for gate tests."""
    result = MagicMock()
    result.success = success
    result.final_output = {"score": score} if score is not None else "raw markdown"
    result.cost_report.total_cost = cost
    return result


@contextmanager
def _patch_reviews(
    *,
    code_score=None,
    sec_score=None,
    cost=0.01,
    code_raises=False,
    sec_raises=False,
):
    """Patch the gate's CodeReview + SecurityAudit workflows.

    Each patched workflow's ``execute(path=...)`` returns a fake result
    carrying the given score (or raises, to exercise fail-closed).
    """

    def _make_wf(score, raises):
        wf = MagicMock()
        if raises:
            wf.execute = AsyncMock(side_effect=RuntimeError("review boom"))
        else:
            wf.execute = AsyncMock(return_value=_fake_review_result(score, cost=cost))
        return wf

    with (
        patch(
            "attune.workflows.code_review.CodeReviewWorkflow",
            return_value=_make_wf(code_score, code_raises),
        ),
        patch(
            "attune.workflows.security_audit.SecurityAuditWorkflow",
            return_value=_make_wf(sec_score, sec_raises),
        ),
    ):
        yield


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
        """A below-threshold review score fails the gate and stops early."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        with _patch_reviews(code_score=40.0, sec_score=90.0):
            result = await orch.run_gates_for_task(task)

        assert result.executed
        assert result.quality_gate_passed is False
        assert result.tests_passed is None

    @pytest.mark.asyncio
    async def test_gate_success(self):
        """Passing review scores record the real scores and summed cost."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        with _patch_reviews(code_score=88.0, sec_score=92.0, cost=0.05):
            result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed
        gate = result.gate_details["gate_results"]
        assert gate["min_quality"]["score"] == 88.0
        assert gate["min_security"]["score"] == 92.0
        # One file, two dimensions at 0.05 each.
        assert result.cost == pytest.approx(0.10)

    @pytest.mark.asyncio
    async def test_gate_fails_closed_on_review_error(self):
        """A review raising fails the gate closed — never a fake pass."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        with _patch_reviews(code_score=95.0, sec_score=95.0, sec_raises=True):
            result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed is False

    @pytest.mark.asyncio
    async def test_gate_no_score_fails_closed(self):
        """A review with no parseable score fails the gate closed."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task()

        # code_score=None -> final_output is raw text, no score.
        with _patch_reviews(code_score=None, sec_score=95.0):
            result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed is False

    @pytest.mark.asyncio
    async def test_gate_no_target_files_passes(self):
        """A task with no file changes passes the gate trivially."""
        orch = PipelineOrchestrator(
            ".claude/plans/pipeline-orchestrator.md",
            skip_tests=True,
            skip_simplify=True,
        )
        task = _make_task(files_to_create=[], files_to_modify=[])

        result = await orch.run_gates_for_task(task)

        assert result.quality_gate_passed


class TestExtractScoreRealAdapter:
    """Non-mocked receipt: _extract_score reads scores from the REAL
    AgentSDKResultAdapter output, not just hand-built dicts.

    Guards the regression where a clean review (score, no findings)
    leaves final_output as raw markdown rather than a WorkflowReport
    dict — without the raw-text fallback the gate would fail closed on
    every such review, turning always-pass theater into always-fail.
    """

    def _real_result(self, text: str):
        from datetime import datetime

        from attune.workflows.agent_sdk_adapter import AgentSDKResultAdapter

        return AgentSDKResultAdapter.from_agent_output(
            report_title="Code review",
            result_text=text,
            subagent_names=[],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    def test_clean_review_no_findings_yields_score(self):
        """A clean review (raw-text final_output) still yields a score."""
        result = self._real_result("Overall assessment.\n\nScore: 95/100\n\nNo issues.")
        assert PipelineOrchestrator._extract_score(result) == 95.0

    def test_low_review_yields_score(self):
        """A low-score review yields the real score for the gate."""
        result = self._real_result("## Findings\n\n- CRITICAL: bad\n\nScore: 35/100")
        assert PipelineOrchestrator._extract_score(result) == 35.0

    def test_no_score_text_fails_closed(self):
        """A review with no score string yields None (gate fails closed)."""
        result = self._real_result("Looks fine to me, no number here.")
        assert PipelineOrchestrator._extract_score(result) is None


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

        mock_wf = AsyncMock()
        mock_wf.execute.side_effect = RuntimeError("simplify broke")

        with patch(
            "attune.workflows.simplify_code.SimplifyCodeWorkflow",
            return_value=mock_wf,
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

        with _patch_reviews(code_score=30.0, sec_score=95.0):
            result = await orch.run_all()

        # Should stop after first task fails
        assert len(result.tasks) == 1
        assert not result.success


# ====================================================================
# Callback + resume tests (for /spec approval loop)
# ====================================================================


class TestRunAllWithCallback:
    """Tests for run_all() on_task_complete callback support."""

    @pytest.mark.asyncio
    async def test_callback_receives_task_and_result(self):
        """Callback is called with task and result after each task."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        received = []

        async def on_complete(task, result):
            received.append((task.task_id, result.task_id))
            return "approve"

        await orch.run_all(on_task_complete=on_complete)

        assert len(received) == 5
        assert received[0][0] == "1"

    @pytest.mark.asyncio
    async def test_callback_none_is_backward_compatible(self):
        """No callback = existing behavior (all tasks run)."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        result = await orch.run_all(on_task_complete=None)
        assert len(result.tasks) == 5

    @pytest.mark.asyncio
    async def test_callback_stop_halts_pipeline(self):
        """Returning 'stop' from callback halts after that task."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        async def on_complete(task, result):
            return "stop" if task.task_id == "2" else "approve"

        result = await orch.run_all(on_task_complete=on_complete)
        assert len(result.tasks) == 2

    @pytest.mark.asyncio
    async def test_callback_auto_skips_future_callbacks(self):
        """Returning 'auto' skips callback for remaining tasks."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        call_count = 0

        async def on_complete(task, result):
            nonlocal call_count
            call_count += 1
            return "auto" if task.task_id == "1" else "approve"

        result = await orch.run_all(on_task_complete=on_complete)
        assert len(result.tasks) == 5
        assert call_count == 1  # Only called once before auto-run kicked in


class TestRunAllWithSkipTaskIds:
    """Tests for run_all() skip_task_ids (resume) support."""

    @pytest.mark.asyncio
    async def test_skips_completed_tasks(self):
        """Tasks in skip_task_ids are not executed."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        result = await orch.run_all(skip_task_ids={"1", "2", "3"})
        assert len(result.tasks) == 2
        task_ids = [t.task_id for t in result.tasks]
        assert "1" not in task_ids
        assert "4" in task_ids

    @pytest.mark.asyncio
    async def test_empty_skip_set_runs_all(self):
        """Empty skip set runs all tasks."""
        orch = PipelineOrchestrator("fake.md", skip_gates=True, skip_tests=True, skip_simplify=True)

        result = await orch.run_all(skip_task_ids=set())
        assert len(result.tasks) == 5


class TestCallbackRedo:
    """Tests for the 'redo' callback path."""

    @pytest.mark.asyncio
    async def test_callback_redo_reruns_task(self):
        """Returning 'redo' pops the result and re-runs the task."""
        orch = PipelineOrchestrator(
            "fake.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=True,
        )

        redo_fired = {"count": 0}

        async def on_complete(task, result):
            # Redo task "2" once, approve everything else
            if task.task_id == "2" and redo_fired["count"] == 0:
                redo_fired["count"] += 1
                return "redo"
            return "approve"

        pipeline_result = await orch.run_all(on_task_complete=on_complete)

        # All 5 tasks should still appear in results
        assert len(pipeline_result.tasks) == 5
        # Task 2 was run, redone, and the redo result kept
        assert redo_fired["count"] == 1


class TestRunGatesTestFailurePath:
    """Tests for the test-failure early-return path."""

    @pytest.mark.asyncio
    async def test_test_failure_skips_simplify(self):
        """When tests fail, simplify is skipped and result reflects failure."""
        orch = PipelineOrchestrator(
            "fake.md",
            skip_gates=True,
            skip_tests=False,
            skip_simplify=False,
        )
        task = _make_task()

        with (
            patch.object(orch, "_find_test_files", return_value=["tests/test_x.py"]),
            patch.object(orch, "_run_tests", return_value=False),
        ):
            result = await orch.run_gates_for_task(task)

        assert result.tests_passed is False
        assert not result.simplified

    @pytest.mark.asyncio
    async def test_test_success_continues_to_simplify(self):
        """When tests pass, simplification runs."""
        orch = PipelineOrchestrator(
            "fake.md",
            skip_gates=True,
            skip_tests=False,
            skip_simplify=False,
        )
        task = _make_task()

        with (
            patch.object(orch, "_find_test_files", return_value=["tests/test_x.py"]),
            patch.object(orch, "_run_tests", return_value=True),
            patch(
                "attune.workflows.simplify_code.SimplifyCodeWorkflow",
            ) as mock_simplify_cls,
        ):
            mock_simplify_cls.return_value = AsyncMock()
            result = await orch.run_gates_for_task(task)

        assert result.tests_passed is True
        assert result.simplified


class TestRunAllResultsReset:
    """Test that run_all resets results on each call."""

    @pytest.mark.asyncio
    async def test_second_call_does_not_accumulate(self):
        """Calling run_all twice doesn't accumulate results."""
        orch = PipelineOrchestrator(
            "fake.md",
            skip_gates=True,
            skip_tests=True,
            skip_simplify=True,
        )

        result1 = await orch.run_all()
        assert len(result1.tasks) == 5

        result2 = await orch.run_all()
        assert len(result2.tasks) == 5  # Not 10
