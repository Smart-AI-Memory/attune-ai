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
    stages = attrs.get("stages", ["analyze", "generate"])
    defaults = {
        "name": "test-workflow",
        "description": "A test workflow",
        "stages": stages,
        # _stage_index is a cached_property on TierRoutingMixin in production;
        # bare-ExecutionMixin stubs need it set explicitly so _update_heartbeat
        # exercises the real beat path (not an AttributeError-swallow path).
        "_stage_index": {n: i for i, n in enumerate(stages)},
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
    async def test_model_refusal_branch_records_fable_refusal_event(self):
        """ModelRefusalError errors the run AND records the telemetry event."""
        from attune.model_tiers import ModelRefusalError

        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(
            side_effect=ModelRefusalError("refused", category="safety")
        )
        obj._finalize_execution = MagicMock(return_value=self._make_result())

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
            patch("attune.models.telemetry.log_fable_refusal") as mock_log,
        ):
            MockRR.return_value = MagicMock()
            result = await obj.execute(task="x")

        assert result.success is False
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["workflow"] == "test-workflow"

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


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestSetupTierTrackingHappyPath:
    """Cover lines 119-122: files_affected normalization + show_recommendation."""

    def test_files_affected_as_list_passed_through(self):
        obj = _make_mixin(_enable_tier_tracking=True)
        fake_tracker = MagicMock()
        with patch(
            "attune.workflows.tier_tracking.WorkflowTierTracker",
            return_value=fake_tracker,
            create=True,
        ):
            obj._setup_tier_tracking({"files_affected": ["a.py", "b.py"]})
        fake_tracker.show_recommendation.assert_called_once_with(["a.py", "b.py"])

    def test_files_affected_as_str_normalized_to_list(self):
        """Line 121: non-list files_affected gets wrapped."""
        obj = _make_mixin(_enable_tier_tracking=True)
        fake_tracker = MagicMock()
        with patch(
            "attune.workflows.tier_tracking.WorkflowTierTracker",
            return_value=fake_tracker,
            create=True,
        ):
            obj._setup_tier_tracking({"path": "src/main.py"})
        fake_tracker.show_recommendation.assert_called_once_with(["src/main.py"])


class TestSetupProgressTrackingExtras:
    """Cover line 144 (callback) + 149-150 (rich happy path)."""

    def test_progress_callback_added(self):
        cb = MagicMock()
        obj = _make_mixin(_enable_rich_progress=False, _progress_callback=cb)
        mock_tracker = MagicMock()
        with (
            patch(
                "attune.workflows.progress.ProgressTracker",
                return_value=mock_tracker,
            ),
            patch("attune.workflows.progress.RICH_AVAILABLE", False),
            patch("attune.workflows.progress.ConsoleProgressReporter"),
        ):
            obj._setup_progress_tracking()
        # add_callback should have been called with our user callback
        called_args = [c.args[0] for c in mock_tracker.add_callback.call_args_list]
        assert cb in called_args

    def test_rich_reporter_happy_path(self):
        """Lines 147-150: RichProgressReporter created, callback added, started."""
        obj = _make_mixin(_enable_rich_progress=True)
        mock_tracker = MagicMock()
        mock_rich = MagicMock()
        with (
            patch(
                "attune.workflows.progress.ProgressTracker",
                return_value=mock_tracker,
            ),
            patch("attune.workflows.progress.RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch(
                "attune.workflows.progress.RichProgressReporter",
                return_value=mock_rich,
            ),
            patch("attune.workflows.progress.ConsoleProgressReporter"),
        ):
            mock_stdout.isatty.return_value = True
            obj._setup_progress_tracking()
        assert obj._rich_reporter is mock_rich
        mock_rich.start.assert_called_once()


class TestStartHeartbeatHappyPath:
    """Cover line 182: heartbeat coordinator success log."""

    def test_heartbeat_started_logs(self):
        obj = _make_mixin()
        coordinator = MagicMock()
        # Should not raise
        obj._start_heartbeat(coordinator)
        coordinator.start_heartbeat.assert_called_once()


class TestExecuteAgentIdAndTierFallback:
    """Cover lines 221, 225, 239 (tier fallback + agent_id None)."""

    @pytest.mark.asyncio
    async def test_agent_id_assigned_when_none(self):
        """Line 225: _agent_id None → assigned from name + run_id prefix."""
        obj = _make_full_workflow()
        obj._agent_id = None
        obj._execute_standard = AsyncMock(return_value={"output": "ok"})
        result_mock = MagicMock(success=True, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
            patch(
                "attune.workflows.suggestions.generate_suggestions", return_value=[], create=True
            ),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        # _agent_id should be set to "{name}-{run_id[:8]}"
        assert obj._agent_id is not None
        assert obj._agent_id.startswith("test-workflow-")

    @pytest.mark.asyncio
    async def test_tier_tracking_setup_invoked(self):
        """Line 221: _enable_tier_tracking=True → _setup_tier_tracking called."""
        obj = _make_full_workflow()
        obj._enable_tier_tracking = True
        obj._setup_tier_tracking = MagicMock()
        obj._execute_standard = AsyncMock(return_value={"output": "ok"})
        result_mock = MagicMock(success=True, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
            patch(
                "attune.workflows.suggestions.generate_suggestions", return_value=[], create=True
            ),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        obj._setup_tier_tracking.assert_called_once()

    @pytest.mark.asyncio
    async def test_tier_fallback_branch_invoked(self):
        """Line 239: _enable_tier_fallback=True → _execute_tier_fallback called."""
        obj = _make_full_workflow()
        obj._enable_tier_fallback = True
        obj._execute_tier_fallback = AsyncMock(return_value={"output": "ok"})
        obj._execute_standard = AsyncMock()
        result_mock = MagicMock(success=True, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
            patch(
                "attune.workflows.suggestions.generate_suggestions", return_value=[], create=True
            ),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        obj._execute_tier_fallback.assert_awaited_once()
        obj._execute_standard.assert_not_called()


class TestExecuteFailWorkflowOnError:
    """Cover lines 255, 260, 265, 271: progress_tracker.fail_workflow in each branch."""

    @pytest.mark.asyncio
    async def test_value_error_calls_fail_workflow(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=ValueError("bad"))
        tracker = MagicMock()
        obj._setup_progress_tracking = MagicMock(
            side_effect=lambda: setattr(obj, "_progress_tracker", tracker)
        )
        result_mock = MagicMock(success=False, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        tracker.fail_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_runtime_error_calls_fail_workflow(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=RuntimeError("API"))
        tracker = MagicMock()
        obj._setup_progress_tracking = MagicMock(
            side_effect=lambda: setattr(obj, "_progress_tracker", tracker)
        )
        result_mock = MagicMock(success=False, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        tracker.fail_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_oserror_calls_fail_workflow(self):
        obj = _make_full_workflow()
        obj._execute_standard = AsyncMock(side_effect=OSError("io"))
        tracker = MagicMock()
        obj._setup_progress_tracking = MagicMock(
            side_effect=lambda: setattr(obj, "_progress_tracker", tracker)
        )
        result_mock = MagicMock(success=False, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        tracker.fail_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_generic_exception_calls_fail_workflow(self):
        obj = _make_full_workflow()

        class _Wat(Exception):
            pass

        obj._execute_standard = AsyncMock(side_effect=_Wat("?"))
        tracker = MagicMock()
        obj._setup_progress_tracking = MagicMock(
            side_effect=lambda: setattr(obj, "_progress_tracker", tracker)
        )
        result_mock = MagicMock(success=False, suggestions=[])
        obj._finalize_execution = MagicMock(return_value=result_mock)

        with (
            patch("attune.models.TaskRoutingRecord", create=True) as MockRR,
            patch("attune.workflows.execution_mixin._update_routing_record"),
        ):
            MockRR.return_value = MagicMock()
            await obj.execute(task="x")
        tracker.fail_workflow.assert_called_once()


class TestExecuteStandardNoProgressTracker:
    """Lines 349->352 and 387->395: progress_tracker None branches."""

    @pytest.mark.asyncio
    async def test_no_tracker_does_not_call_start_or_complete(self):
        obj = _make_mixin(stages=["only"])
        obj._get_tier_with_routing = MagicMock(return_value=MagicMock(value="cheap"))
        obj.should_skip_stage = MagicMock(return_value=(False, None))
        obj.get_model_for_tier = MagicMock(return_value="m")
        obj._state_record_stage_start = MagicMock()
        obj._state_record_stage_complete = MagicMock()
        obj._calculate_cost = MagicMock(return_value=0.1)
        obj._track_telemetry = MagicMock()
        obj.validate_contract = MagicMock()
        obj.run_stage = AsyncMock(return_value=({"output": "ok"}, 10, 5))
        obj._progress_tracker = None  # line 349->352 + 387->395

        from attune.workflows.data_classes import WorkflowStage

        result = await obj._execute_standard({}, WorkflowStage)
        assert result == {"output": "ok"}


class TestExecuteTierFallback:
    """Cover lines 442-519: _execute_tier_fallback body."""

    def _setup(self, stages=None):
        obj = _make_mixin(stages=stages or ["analyze"], _enable_tier_fallback=True)
        obj.get_model_for_tier = MagicMock(return_value="model-x")
        obj.should_skip_stage = MagicMock(return_value=(False, None))
        obj._state_record_stage_start = MagicMock()
        obj._state_record_stage_complete = MagicMock()
        obj._calculate_cost = MagicMock(return_value=0.01)
        obj._track_telemetry = MagicMock()
        obj.validate_contract = MagicMock()
        obj.validate_output = MagicMock(return_value=(True, None))
        obj._handle_stage_skip = MagicMock()
        obj._record_stage_success = MagicMock()
        obj._report_stage_progress = MagicMock()
        obj._update_heartbeat = MagicMock()
        obj._log_tier_failure = MagicMock()
        return obj

    @pytest.mark.asyncio
    async def test_first_tier_succeeds(self):
        """Cheap tier succeeds → break out of inner loop."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup()
        obj.run_stage = AsyncMock(return_value=({"k": "v"}, 10, 5))
        result = await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)
        assert result == {"k": "v"}
        obj._record_stage_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_skipped_stage_in_fallback(self):
        """Lines 446-448: should_skip True → _handle_stage_skip called, continue."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup(stages=["a", "b"])
        # Skip first stage, run second
        obj.should_skip_stage = MagicMock(side_effect=[(True, "skip"), (False, None)])
        obj.run_stage = AsyncMock(return_value=({"k": "v"}, 10, 5))
        await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)
        obj._handle_stage_skip.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_fails_tries_next_tier(self):
        """Lines 493-500: validate_output False → log + try next tier."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup()
        # First call: invalid; second call: valid
        obj.validate_output = MagicMock(side_effect=[(False, "low_quality"), (True, None)])
        obj.run_stage = AsyncMock(return_value=({"k": "v"}, 10, 5))
        await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)
        # _log_tier_failure called for failure
        assert obj._log_tier_failure.called
        # Eventually succeeded
        obj._record_stage_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_stage_raises_tries_next_tier(self):
        """Lines 502-511: run_stage raises → log warning + try next tier."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup()
        # First: raise; second: success
        obj.run_stage = AsyncMock(side_effect=[RuntimeError("err"), ({"k": "v"}, 10, 5)])
        await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)
        assert obj._log_tier_failure.called

    @pytest.mark.asyncio
    async def test_all_tiers_fail_raises_value_error(self):
        """Lines 513-517: stage_succeeded False → ValueError raised."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup()
        obj.run_stage = AsyncMock(side_effect=RuntimeError("always fail"))
        tracker = MagicMock()
        obj._progress_tracker = tracker
        with pytest.raises(ValueError, match="failed with all tiers"):
            await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)
        tracker.fail_stage.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_tiers_fail_no_progress_tracker(self):
        """Line 515->517: tracker None branch when all tiers fail."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        obj = self._setup()
        obj.run_stage = AsyncMock(side_effect=RuntimeError("always fail"))
        obj._progress_tracker = None
        with pytest.raises(ValueError, match="failed with all tiers"):
            await obj._execute_tier_fallback({}, None, ModelTier, WorkflowStage)


class TestHandleStageSkip:
    """Lines 528-538: _handle_stage_skip body."""

    def test_appends_skipped_stage(self):
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin()
        obj.get_tier_for_stage = MagicMock(return_value=MagicMock(value="cheap"))
        obj._handle_stage_skip("analyze", "already done", WorkflowStage)
        assert len(obj._stages_run) == 1
        assert obj._stages_run[0].skipped is True

    def test_no_progress_tracker(self):
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin(_progress_tracker=None)
        obj.get_tier_for_stage = MagicMock(return_value=MagicMock(value="cheap"))
        # Should not raise even without tracker
        obj._handle_stage_skip("analyze", "skip", WorkflowStage)

    def test_with_progress_tracker(self):
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin()
        obj.get_tier_for_stage = MagicMock(return_value=MagicMock(value="cheap"))
        tracker = MagicMock()
        obj._progress_tracker = tracker
        obj._handle_stage_skip("analyze", "skip me", WorkflowStage)
        tracker.skip_stage.assert_called_once_with("analyze", "skip me")


class TestRecordStageSuccess:
    """Lines 595-636: _record_stage_success body."""

    def test_records_full_success_path(self):
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin()
        obj.cost_tracker = MagicMock()
        obj._track_telemetry = MagicMock()
        obj._update_heartbeat = MagicMock()
        obj._state_record_stage_complete = MagicMock()
        tracker = MagicMock()
        obj._progress_tracker = tracker

        tier = MagicMock()
        tier.value = "cheap"
        obj._record_stage_success(
            "analyze",
            tier,
            "model-x",
            WorkflowStage,
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            output={"k": "v"},
            duration_ms=42,
            heartbeat_coordinator=MagicMock(),
        )
        assert len(obj._stages_run) == 1
        tracker.complete_stage.assert_called_once()
        obj.cost_tracker.log_request.assert_called_once()
        obj._track_telemetry.assert_called_once()
        obj._state_record_stage_complete.assert_called_once_with("analyze", 0.001, 42, "cheap")
        # Tier progression appended
        assert obj._tier_progression == [("analyze", "cheap", True)]

    def test_no_progress_tracker(self):
        """Branch where _progress_tracker is None."""
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin(_progress_tracker=None)
        obj.cost_tracker = MagicMock()
        obj._track_telemetry = MagicMock()
        obj._update_heartbeat = MagicMock()
        obj._state_record_stage_complete = MagicMock()

        tier = MagicMock()
        tier.value = "premium"
        obj._record_stage_success(
            "s",
            tier,
            "m",
            WorkflowStage,
            input_tokens=1,
            output_tokens=2,
            cost=0.5,
            output="result",
            duration_ms=10,
            heartbeat_coordinator=None,
        )
        assert len(obj._stages_run) == 1


class TestLogTierFailure:
    """Lines 648-663: _log_tier_failure body."""

    def test_info_level_with_more_tiers(self):
        obj = _make_mixin()
        tier = MagicMock()
        tier.value = "cheap"
        capable = MagicMock()
        capable.value = "capable"
        # tier_index 0 of 2 → not exhausted, retrying message
        obj._log_tier_failure("s", tier, 0, [tier, capable], "low_quality", "info")
        assert obj._tier_progression == [("s", "cheap", False)]

    def test_warning_level_last_tier_exhausted(self):
        obj = _make_mixin()
        tier = MagicMock()
        tier.value = "premium"
        cheap = MagicMock()
        cheap.value = "cheap"
        # last tier_index → exhausted
        obj._log_tier_failure("s", tier, 1, [cheap, tier], "boom", "warning")
        assert obj._tier_progression == [("s", "premium", False)]

    def test_invalid_log_level_falls_back_to_info(self):
        """Line 650: getattr(logger, level, logger.info) — unknown level."""
        obj = _make_mixin()
        tier = MagicMock()
        tier.value = "cheap"
        # No exception even with bogus level
        obj._log_tier_failure("s", tier, 0, [tier], "x", level="not-a-real-level")


class TestFinalizeExecutionMissingBranches:
    """Cover lines 699-701, 706, 723->726, 757."""

    def test_final_output_picked_from_last_completed_stage(self):
        """Lines 699-701: reverse loop finds non-skipped non-None result."""
        from attune.workflows.data_classes import WorkflowStage

        obj = _make_mixin()
        obj._stages_run = [
            WorkflowStage(name="s1", tier=MagicMock(), description="", result={"a": 1}),
            WorkflowStage(name="s2", tier=MagicMock(), description="", skipped=True),
        ]
        obj._generate_cost_report = MagicMock(return_value={})
        obj._emit_workflow_telemetry = MagicMock()
        obj._state_record_workflow_complete = MagicMock()
        obj._save_tier_progression = MagicMock()

        result_holder = {}

        def make_result(**kw):
            result_holder.update(kw)
            r = MagicMock()
            r.success = kw.get("success")
            r.error = kw.get("error")
            r.stages = kw.get("stages")
            return r

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=datetime.now(timezone.utc),
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=make_result,
                _save_workflow_run=MagicMock(),
            )
        # final_output should be picked from s1 (last non-skipped, non-None result)
        assert result_holder["final_output"] == {"a": 1}

    def test_error_classify_invoked(self):
        """Line 706: error not None → _classify_error called."""
        obj = _make_mixin()
        obj._stages_run = []
        obj._generate_cost_report = MagicMock(return_value={})
        obj._emit_workflow_telemetry = MagicMock()
        obj._state_record_workflow_complete = MagicMock()
        obj._save_tier_progression = MagicMock()

        result_holder = {}

        def make_result(**kw):
            result_holder.update(kw)
            r = MagicMock()
            r.success = kw.get("success")
            r.error = kw.get("error")
            r.error_type = kw.get("error_type")
            r.transient = kw.get("transient")
            r.stages = kw.get("stages")
            return r

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=datetime.now(timezone.utc),
                error="Workflow execution error: timeout occurred",
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=make_result,
                _save_workflow_run=MagicMock(),
            )
        assert result_holder["error_type"] == "timeout"
        assert result_holder["transient"] is True

    def test_progress_tracker_complete_workflow_called_when_no_error(self):
        """Line 723->726: progress_tracker truthy AND error None → complete_workflow."""
        obj = _make_mixin()
        obj._stages_run = []
        obj._generate_cost_report = MagicMock(return_value={})
        obj._emit_workflow_telemetry = MagicMock()
        obj._state_record_workflow_complete = MagicMock()
        obj._save_tier_progression = MagicMock()
        tracker = MagicMock()
        obj._progress_tracker = tracker

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=datetime.now(timezone.utc),
                error=None,
                heartbeat_coordinator=None,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(
                    return_value=MagicMock(success=True, error=None, stages=[])
                ),
                _save_workflow_run=MagicMock(),
            )
        tracker.complete_workflow.assert_called_once()

    def test_heartbeat_stop_happy_path_logs(self):
        """Line 757: heartbeat_coordinator.stop_heartbeat success path."""
        obj = _make_mixin()
        obj._stages_run = []
        obj._generate_cost_report = MagicMock(return_value={})
        obj._emit_workflow_telemetry = MagicMock()
        obj._state_record_workflow_complete = MagicMock()
        obj._save_tier_progression = MagicMock()
        coordinator = MagicMock()

        with patch("attune.workflows.execution_mixin._update_routing_record"):
            obj._finalize_execution(
                kwargs={},
                started_at=datetime.now(timezone.utc),
                error=None,
                heartbeat_coordinator=coordinator,
                routing_record=MagicMock(),
                WorkflowResult=MagicMock(
                    return_value=MagicMock(success=True, error=None, stages=[])
                ),
                _save_workflow_run=MagicMock(),
            )
        coordinator.stop_heartbeat.assert_called_once_with(final_status="completed")


class TestSaveTierProgression:
    """Lines 775-803: _save_tier_progression body."""

    def test_disabled_returns_early(self):
        """Line 775-776: tier tracking disabled → return."""
        obj = _make_mixin(_enable_tier_tracking=False)
        # Should not raise even without _tier_tracker
        obj._save_tier_progression({}, MagicMock())

    def test_no_tracker_returns_early(self):
        obj = _make_mixin(_enable_tier_tracking=True, _tier_tracker=None)
        obj._save_tier_progression({}, MagicMock())  # no-op

    def test_saves_progression_with_files_affected_list(self):
        obj = _make_mixin(_enable_tier_tracking=True)
        tracker = MagicMock()
        obj._tier_tracker = tracker
        obj._enable_tier_fallback = True
        obj._tier_progression = [("s1", "cheap", True)]
        obj._save_tier_progression(
            {"files_affected": ["x.py"]},
            MagicMock(),
        )
        tracker.save_progression.assert_called_once()
        call_kwargs = tracker.save_progression.call_args.kwargs
        assert call_kwargs["files_affected"] == ["x.py"]
        assert call_kwargs["tier_progression"] == [("s1", "cheap", True)]

    def test_saves_progression_with_str_path_normalized(self):
        obj = _make_mixin(_enable_tier_tracking=True)
        tracker = MagicMock()
        obj._tier_tracker = tracker
        obj.name = "code-review"  # mapped bug type
        obj._save_tier_progression({"path": "src/main.py"}, MagicMock())
        kwargs = tracker.save_progression.call_args.kwargs
        assert kwargs["files_affected"] == ["src/main.py"]
        assert kwargs["bug_type"] == "code_quality"

    def test_unknown_workflow_uses_default_bug_type(self):
        """bug_type_map.get fallback → 'workflow_run'."""
        obj = _make_mixin(_enable_tier_tracking=True)
        tracker = MagicMock()
        obj._tier_tracker = tracker
        obj.name = "custom-workflow-not-mapped"
        obj._save_tier_progression({}, MagicMock())
        assert tracker.save_progression.call_args.kwargs["bug_type"] == "workflow_run"

    def test_no_tier_fallback_passes_none_progression(self):
        """Line 793: _enable_tier_fallback False → tier_progression=None."""
        obj = _make_mixin(_enable_tier_tracking=True)
        tracker = MagicMock()
        obj._tier_tracker = tracker
        obj._enable_tier_fallback = False
        obj._tier_progression = [("s", "cheap", True)]
        obj._save_tier_progression({}, MagicMock())
        assert tracker.save_progression.call_args.kwargs["tier_progression"] is None

    def test_exception_during_save_swallowed(self):
        """Lines 801-803: tracker raises → caught + debug log."""
        obj = _make_mixin(_enable_tier_tracking=True)
        tracker = MagicMock()
        tracker.save_progression.side_effect = RuntimeError("save failed")
        obj._tier_tracker = tracker
        obj._save_tier_progression({}, MagicMock())  # no raise


class TestClassifyError:
    """Lines 821-830: _classify_error branches."""

    def test_timeout(self):
        from attune.workflows.execution_mixin import _classify_error

        assert _classify_error("timeout occurred") == ("timeout", True)
        assert _classify_error("request timed out") == ("timeout", True)

    def test_config(self):
        from attune.workflows.execution_mixin import _classify_error

        assert _classify_error("invalid config") == ("config", False)
        assert _classify_error("missing configuration") == ("config", False)

    def test_provider(self):
        from attune.workflows.execution_mixin import _classify_error

        assert _classify_error("api error") == ("provider", True)
        assert _classify_error("rate limit hit") == ("provider", True)
        assert _classify_error("quota exceeded") == ("provider", True)

    def test_validation(self):
        from attune.workflows.execution_mixin import _classify_error

        assert _classify_error("validation failed") == ("validation", False)
        assert _classify_error("invalid input") == ("validation", False)

    def test_runtime_default(self):
        from attune.workflows.execution_mixin import _classify_error

        assert _classify_error("something else") == ("runtime", False)


class TestUpdateRoutingRecord:
    """Lines 842-856: _update_routing_record body."""

    def test_success_path(self):
        from attune.workflows.execution_mixin import _update_routing_record

        rr = MagicMock()
        result = MagicMock()
        result.success = True
        result.error = None
        result.error_type = None
        result.stages = [MagicMock(cost=0.1), MagicMock(cost=0.2)]

        wf = MagicMock()
        wf._telemetry_backend = MagicMock()
        _update_routing_record(wf, rr, result)

        assert rr.status == "completed"
        assert rr.success is True
        assert abs(rr.actual_cost - 0.3) < 1e-9
        wf._telemetry_backend.log_task_routing.assert_called_once_with(rr)

    def test_failure_with_error(self):
        from attune.workflows.execution_mixin import _update_routing_record

        rr = MagicMock()
        result = MagicMock()
        result.success = False
        result.error = "something bad"
        result.error_type = "timeout"
        result.stages = []

        wf = MagicMock()
        wf._telemetry_backend = None
        _update_routing_record(wf, rr, result)

        assert rr.status == "failed"
        assert rr.error_type == "timeout"
        assert rr.error_message == "something bad"

    def test_failure_with_unknown_error_type(self):
        """Line 848: error_type fallback to 'unknown'."""
        from attune.workflows.execution_mixin import _update_routing_record

        rr = MagicMock()
        result = MagicMock()
        result.success = False
        result.error = "boom"
        result.error_type = None
        result.stages = []

        wf = MagicMock()
        wf._telemetry_backend = None
        _update_routing_record(wf, rr, result)
        assert rr.error_type == "unknown"

    def test_telemetry_log_exception_swallowed(self):
        """Lines 854-856: telemetry log exception caught."""
        from attune.workflows.execution_mixin import _update_routing_record

        rr = MagicMock()
        result = MagicMock(success=True, error=None, error_type=None, stages=[])
        wf = MagicMock()
        wf._telemetry_backend = MagicMock()
        wf._telemetry_backend.log_task_routing.side_effect = RuntimeError("telemetry down")
        # Should not raise
        _update_routing_record(wf, rr, result)
