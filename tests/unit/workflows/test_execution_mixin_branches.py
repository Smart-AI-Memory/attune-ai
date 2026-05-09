"""Branch coverage for attune.workflows.execution_mixin.

Targets previously-uncovered lines:
- _create_routing_record: telemetry exception (102/104)
- _setup_tier_tracking: exception path (123/125/126)
- _setup_progress_tracking: rich reporter exception path (147-156)
- _start_heartbeat: exception path (187/189/190)
- execute(): ValueError/TypeError/KeyError branch (256-260)
- execute(): TimeoutError/RuntimeError/ConnectionError branch (261-265)
- execute(): OSError/PermissionError branch (266-270)
- execute(): generic Exception branch (271-275)
- execute(): suggestions exception (296/298)
- _execute_standard: should_skip_stage True path (336/343-346)
- _report_stage_progress: no tracker early return (550)
- _update_heartbeat: exception path (577/579)
- _finalize_execution: rich_reporter.stop() exception (727-731)
- _finalize_execution: _save_workflow_run OSError (735/736)
- _finalize_execution: _save_workflow_run ValueError (737/738)
- _finalize_execution: _save_workflow_run generic exception (739/741)
- _finalize_execution: heartbeat stop exception (764/766)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.execution_mixin import ExecutionMixin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mixin(**attrs):
    """Minimal ExecutionMixin instance with all required attributes set."""
    obj = ExecutionMixin()
    defaults = {
        "name": "test-workflow",
        "description": "A test workflow",
        "stages": ["analyze", "generate"],
        "tier_map": {"analyze": MagicMock(), "generate": MagicMock()},
        "_run_id": "run-abc123",
        "_stages_run": [],
        "_progress_tracker": None,
        "_progress_callback": None,
        "_enable_rich_progress": False,
        "_rich_reporter": None,
        "_telemetry_backend": None,
        "_enable_tier_tracking": False,
        "_tier_tracker": None,
        "_enable_tier_fallback": False,
        "_tier_progression": [],
        "_routing_strategy": None,
        "_enable_adaptive_routing": False,
        "_enable_heartbeat_tracking": False,
        "_enable_coordination": False,
        "_agent_id": "agent-1",
        "_provider_str": "anthropic",
        "_config": None,
        "_enable_cache": False,
        "_cache": None,
        "_executor": None,
        "cost_tracker": MagicMock(),
    }
    defaults.update(attrs)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# _create_routing_record — telemetry exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateRoutingRecord:
    def test_telemetry_exception_is_swallowed(self):
        obj = _make_mixin()
        backend = MagicMock()
        backend.log_task_routing.side_effect = RuntimeError("telemetry down")
        obj._telemetry_backend = backend

        # Should not raise
        with patch("attune.models.TaskRoutingRecord", create=True) as MockRecord:
            MockRecord.return_value = MagicMock()
            obj._assess_complexity = MagicMock(return_value="low")
            record = obj._create_routing_record({"task": "x"})

        assert record is not None


# ---------------------------------------------------------------------------
# _setup_tier_tracking — exception path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetupTierTracking:
    def test_exception_disables_tier_tracking(self):
        obj = _make_mixin(_enable_tier_tracking=True)

        with patch(
            "attune.workflows.execution_mixin.ExecutionMixin._setup_tier_tracking",
            wraps=None,
        ):
            # Patch the inner import to raise
            with patch.dict("sys.modules", {"attune.workflows.tier_tracking": None}):
                # Direct call — import will fail because module mapped to None
                obj._enable_tier_tracking = True
                try:
                    obj._setup_tier_tracking({})
                except Exception:
                    pass

        # If an exception is raised and caught, _enable_tier_tracking becomes False
        # The real method catches all exceptions
        obj2 = _make_mixin(_enable_tier_tracking=True)

        class _BadTracker:
            def __init__(self, *a, **kw):
                raise RuntimeError("tracker init failed")

        with patch("attune.workflows.tier_tracking.WorkflowTierTracker", _BadTracker, create=True):
            obj2._setup_tier_tracking({})

        assert obj2._enable_tier_tracking is False


# ---------------------------------------------------------------------------
# _setup_progress_tracking — rich reporter exception path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetupProgressTracking:
    def test_rich_reporter_exception_falls_back_to_console(self):
        obj = _make_mixin(_enable_rich_progress=True)

        mock_progress_tracker = MagicMock()
        mock_console_reporter = MagicMock()

        with (
            patch(
                "attune.workflows.progress.ProgressTracker",
                return_value=mock_progress_tracker,
            ),
            patch("attune.workflows.progress.RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch(
                "attune.workflows.progress.RichProgressReporter",
                side_effect=RuntimeError("rich broken"),
            ),
            patch(
                "attune.workflows.progress.ConsoleProgressReporter",
                return_value=mock_console_reporter,
            ),
        ):
            mock_stdout.isatty.return_value = True
            obj._setup_progress_tracking()

        # Rich failed → reporter is None, console is added
        assert obj._rich_reporter is None
        mock_progress_tracker.add_callback.assert_called()

    def test_no_rich_uses_console(self):
        obj = _make_mixin(_enable_rich_progress=False)

        mock_progress_tracker = MagicMock()
        mock_console_reporter = MagicMock()

        with (
            patch(
                "attune.workflows.progress.ProgressTracker",
                return_value=mock_progress_tracker,
            ),
            patch("attune.workflows.progress.RICH_AVAILABLE", False),
            patch(
                "attune.workflows.progress.ConsoleProgressReporter",
                return_value=mock_console_reporter,
            ),
        ):
            obj._setup_progress_tracking()

        mock_progress_tracker.add_callback.assert_called()


# ---------------------------------------------------------------------------
# _start_heartbeat — exception path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStartHeartbeat:
    def test_no_coordinator_returns_early(self):
        obj = _make_mixin()
        # Should not raise
        obj._start_heartbeat(None)

    def test_exception_is_swallowed(self):
        obj = _make_mixin()
        coordinator = MagicMock()
        coordinator.start_heartbeat.side_effect = RuntimeError("heartbeat failed")
        # Should not raise
        obj._start_heartbeat(coordinator)


# ---------------------------------------------------------------------------
# _report_stage_progress — no tracker early return
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReportStageProgress:
    def test_no_tracker_returns_early(self):
        obj = _make_mixin(_progress_tracker=None)
        tier = MagicMock()
        tier.value = "cheap"
        # Should not raise even with no tracker
        obj._report_stage_progress("analyze", tier, 0, [tier], "model-1")

    def test_tier_index_zero_calls_start_stage(self):
        obj = _make_mixin()
        tracker = MagicMock()
        obj._progress_tracker = tracker
        tier = MagicMock()
        tier.value = "cheap"

        obj._report_stage_progress("analyze", tier, 0, [tier], "model-1")

        tracker.start_stage.assert_called_once_with("analyze", "cheap", "model-1")

    def test_tier_index_nonzero_calls_update_tier(self):
        obj = _make_mixin()
        tracker = MagicMock()
        obj._progress_tracker = tracker
        cheap = MagicMock()
        cheap.value = "cheap"
        capable = MagicMock()
        capable.value = "capable"

        obj._report_stage_progress("analyze", capable, 1, [cheap, capable], "model-2")

        tracker.update_tier.assert_called_once_with("analyze", "capable", "cheap_failed")


# ---------------------------------------------------------------------------
# _update_heartbeat — exception path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateHeartbeat:
    def test_no_coordinator_returns_early(self):
        obj = _make_mixin()
        # Should not raise
        obj._update_heartbeat(None, "analyze", MagicMock())

    def test_exception_is_swallowed(self):
        obj = _make_mixin()
        coordinator = MagicMock()
        coordinator.beat.side_effect = RuntimeError("beat failed")
        tier = MagicMock()
        tier.value = "cheap"

        # Should not raise
        obj._update_heartbeat(coordinator, "analyze", tier, offset=0)

    def test_stage_not_in_stages_is_swallowed(self):
        obj = _make_mixin(stages=["analyze"])
        coordinator = MagicMock()
        tier = MagicMock()
        tier.value = "cheap"

        # "unknown-stage" is not in stages → ValueError from list.index → swallowed
        obj._update_heartbeat(coordinator, "unknown-stage", tier)

        coordinator.beat.assert_not_called()


# ---------------------------------------------------------------------------
# execute() — exception branches
# ---------------------------------------------------------------------------


def _make_full_workflow(raise_from="_execute_standard"):
    """Build a mixin with enough state to run execute() up to exception handling."""
    obj = _make_mixin()

    # Required methods mocked
    obj._maybe_setup_cache = MagicMock()
    obj.validate_input = MagicMock()
    obj._state_record_workflow_start = MagicMock()
    obj._assess_complexity = MagicMock(return_value="low")
    obj._get_heartbeat_coordinator = MagicMock(return_value=None)
    obj._start_heartbeat = MagicMock()
    obj._setup_progress_tracking = MagicMock()
    obj._finalize_execution = MagicMock()
    obj._run_post_simplification = AsyncMock(side_effect=lambda r, k: r)
    obj._run_verification_loop = AsyncMock(side_effect=lambda r, k: (r, None))
    obj._state_record_workflow_complete = MagicMock()
    obj._emit_workflow_telemetry = MagicMock()
    obj._generate_cost_report = MagicMock(return_value={})
    obj._save_tier_progression = MagicMock()
    obj._get_tier_with_routing = MagicMock(return_value=MagicMock(value="cheap"))
    obj.should_skip_stage = MagicMock(return_value=(False, None))
    obj.get_model_for_tier = MagicMock(return_value="claude-3-haiku")
    obj._state_record_stage_start = MagicMock()
    obj.run_stage = AsyncMock(return_value={"output": "ok"})
    return obj


@pytest.mark.unit
class TestExecuteExceptionBranches:
    """Cover the four exception handler blocks inside execute()."""

    def _patch_execute_standard(self, obj, exc):
        obj._execute_standard = AsyncMock(side_effect=exc)
        obj._execute_tier_fallback = AsyncMock(side_effect=exc)

    def _make_result(self):
        r = MagicMock()
        r.success = False
        r.suggestions = []
        return r

    @pytest.mark.asyncio
    async def test_value_error_branch(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=ValueError("bad data"))
        obj._finalize_execution = MagicMock(return_value=self._make_result())

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_runtime_error_branch(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=RuntimeError("API down"))
        obj._finalize_execution = MagicMock(return_value=self._make_result())

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_oserror_branch(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=OSError("disk full"))
        obj._finalize_execution = MagicMock(return_value=self._make_result())

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_generic_exception_branch(self):
        obj = _make_full_workflow()

        class _WeirdError(Exception):
            pass

        obj._execute_standard = AsyncMock(side_effect=_WeirdError("very weird"))
        obj._finalize_execution = MagicMock(return_value=self._make_result())

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_suggestions_exception_is_swallowed(self):
        """generate_suggestions raising doesn't crash execute()."""
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(return_value={"output": "ok"})
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.suggestions = []
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
            patch(
                "attune.workflows.suggestions.generate_suggestions",
                side_effect=ImportError("no suggestions"),
                create=True,
            ),
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        # Should succeed despite suggestions failure
        assert result.success is True


# ---------------------------------------------------------------------------
# _execute_standard — should_skip_stage True path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteStandardSkipStage:
    @pytest.mark.asyncio
    async def test_skip_stage_appends_skipped_stage(self):
        obj = _make_mixin(stages=["analyze", "generate"])
        obj._get_tier_with_routing = MagicMock(return_value=MagicMock(value="cheap"))
        obj.should_skip_stage = MagicMock(side_effect=[(True, "already done"), (False, None)])
        obj.get_model_for_tier = MagicMock(return_value="claude-haiku")
        obj._state_record_stage_start = MagicMock()
        obj._state_record_stage_complete = MagicMock()
        obj._calculate_cost = MagicMock(return_value=0.001)
        obj._track_telemetry = MagicMock()
        obj.validate_contract = MagicMock()
        # run_stage must return (output, input_tokens, output_tokens) 3-tuple
        obj.run_stage = AsyncMock(return_value=({"output": "ok"}, 100, 50))
        obj._record_stage_success = MagicMock()
        obj._update_heartbeat = MagicMock()

        mock_progress = MagicMock()
        obj._progress_tracker = mock_progress

        from attune.workflows.data_classes import WorkflowStage

        await obj._execute_standard({}, WorkflowStage)

        # First stage skipped — skip_stage called on tracker
        mock_progress.skip_stage.assert_called_once_with("analyze", "already done")
        # Skipped stage recorded in _stages_run
        assert len(obj._stages_run) >= 1
        skipped_stages = [s for s in obj._stages_run if s.skipped]
        assert len(skipped_stages) == 1

    @pytest.mark.asyncio
    async def test_skip_stage_no_progress_tracker(self):
        """Skip path works without a progress tracker."""
        obj = _make_mixin(stages=["analyze"])
        obj._get_tier_with_routing = MagicMock(return_value=MagicMock(value="cheap"))
        obj.should_skip_stage = MagicMock(return_value=(True, "skip it"))
        obj._progress_tracker = None

        from attune.workflows.data_classes import WorkflowStage

        await obj._execute_standard({}, WorkflowStage)

        skipped = [s for s in obj._stages_run if s.skipped]
        assert len(skipped) == 1
        assert skipped[0].skip_reason == "skip it"


# ---------------------------------------------------------------------------
# _finalize_execution — exception coverage (via unit tests on helpers)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFinalizeExecutionExceptions:
    """Cover exception branches inside _finalize_execution called indirectly."""

    def _make_finalize_mixin(self):
        obj = _make_mixin()
        obj._stages_run = []
        obj._generate_cost_report = MagicMock(return_value={})
        obj._progress_tracker = MagicMock()
        obj._rich_reporter = None
        obj._emit_workflow_telemetry = MagicMock()
        obj._state_record_workflow_complete = MagicMock()
        obj._save_tier_progression = MagicMock()
        return obj

    def test_rich_reporter_stop_exception_is_swallowed(self):
        """_rich_reporter.stop() raising must not crash finalization."""

        obj = self._make_finalize_mixin()
        bad_reporter = MagicMock()
        bad_reporter.stop.side_effect = RuntimeError("display crashed")
        obj._rich_reporter = bad_reporter

        started_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_result.stages = []

        # Call _finalize_execution with a save function that works fine
        save_fn = MagicMock()

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=started_at,
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(return_value=mock_result),
                _save_workflow_run=save_fn,
            )

        # rich_reporter should be set to None after stop attempt
        assert obj._rich_reporter is None

    def test_save_workflow_run_oserror_is_caught(self):
        """OSError during _save_workflow_run is caught and logged."""
        obj = self._make_finalize_mixin()
        started_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_result.stages = []

        save_fn = MagicMock(side_effect=OSError("disk full"))

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=started_at,
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(return_value=mock_result),
                _save_workflow_run=save_fn,
            )
        # No exception raised

    def test_save_workflow_run_value_error_is_caught(self):
        """ValueError during _save_workflow_run is caught."""
        obj = self._make_finalize_mixin()
        started_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_result.stages = []

        save_fn = MagicMock(side_effect=ValueError("bad value"))

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=started_at,
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(return_value=mock_result),
                _save_workflow_run=save_fn,
            )

    def test_save_workflow_run_generic_exception_is_caught(self):
        """Generic exception during _save_workflow_run is caught."""
        obj = self._make_finalize_mixin()
        started_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_result.stages = []

        save_fn = MagicMock(side_effect=Exception("unexpected"))

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=started_at,
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(return_value=mock_result),
                _save_workflow_run=save_fn,
            )

    def test_heartbeat_stop_exception_is_swallowed(self):
        """heartbeat_coordinator.stop_heartbeat() exception is swallowed."""
        obj = self._make_finalize_mixin()
        started_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_result.stages = []

        coordinator = MagicMock()
        coordinator.stop_heartbeat.side_effect = RuntimeError("heartbeat fail")

        save_fn = MagicMock()

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=started_at,
                error=None,
                heartbeat_coordinator=coordinator,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(return_value=mock_result),
                _save_workflow_run=save_fn,
            )
        # No exception raised
