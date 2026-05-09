"""Comprehensive coverage tests for Workflow Telemetry Mixin.

Tests TelemetryMixin for tracking LLM calls and workflow executions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import attune.workflows.telemetry_mixin as telemetry_module

TelemetryMixin = telemetry_module.TelemetryMixin


@pytest.mark.unit
class TestTelemetryMixinInitialization:
    """Test TelemetryMixin initialization and attributes."""

    def test_mixin_default_attributes(self):
        """Test TelemetryMixin has correct default attributes."""
        mixin = TelemetryMixin()

        assert mixin._telemetry_backend is None
        assert mixin._telemetry_tracker is None
        assert mixin._enable_telemetry is True
        assert mixin._run_id is None
        assert mixin.name == "unknown"
        assert mixin._provider_str == "unknown"

    @patch("attune.models.get_telemetry_store")
    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.telemetry_mixin.UsageTracker")
    def test_init_telemetry_with_defaults(self, mock_tracker_class, mock_get_store):
        """Test _init_telemetry with default backend."""
        mixin = TelemetryMixin()
        mock_backend = MagicMock()
        mock_get_store.return_value = mock_backend
        mock_tracker = MagicMock()
        mock_tracker_class.get_instance.return_value = mock_tracker

        mixin._init_telemetry()

        assert mixin._telemetry_backend is mock_backend
        assert mixin._telemetry_tracker is mock_tracker
        assert mixin._enable_telemetry is True

    @patch("attune.models.get_telemetry_store")
    def test_init_telemetry_with_custom_backend(self, mock_get_store):
        """Test _init_telemetry with custom backend."""
        mixin = TelemetryMixin()
        custom_backend = MagicMock()

        mixin._init_telemetry(telemetry_backend=custom_backend)

        assert mixin._telemetry_backend is custom_backend
        mock_get_store.assert_not_called()

    @patch("attune.models.get_telemetry_store")
    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.telemetry_mixin.UsageTracker")
    def test_init_telemetry_handles_os_error(self, mock_tracker_class, mock_get_store):
        """Test _init_telemetry handles file system errors gracefully."""
        mixin = TelemetryMixin()
        mock_backend = MagicMock()
        mock_get_store.return_value = mock_backend
        mock_tracker_class.get_instance.side_effect = OSError("File error")

        mixin._init_telemetry()

        assert mixin._enable_telemetry is False

    @patch("attune.models.get_telemetry_store")
    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.telemetry_mixin.UsageTracker")
    def test_init_telemetry_handles_permission_error(self, mock_tracker_class, mock_get_store):
        """Test _init_telemetry handles permission errors gracefully."""
        mixin = TelemetryMixin()
        mock_backend = MagicMock()
        mock_get_store.return_value = mock_backend
        mock_tracker_class.get_instance.side_effect = PermissionError("Permission denied")

        mixin._init_telemetry()

        assert mixin._enable_telemetry is False

    @patch("attune.models.get_telemetry_store")
    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.telemetry_mixin.UsageTracker")
    def test_init_telemetry_handles_attribute_error(self, mock_tracker_class, mock_get_store):
        """Test _init_telemetry handles configuration errors."""
        mixin = TelemetryMixin()
        mock_backend = MagicMock()
        mock_get_store.return_value = mock_backend
        mock_tracker_class.get_instance.side_effect = AttributeError("Missing attribute")

        mixin._init_telemetry()

        assert mixin._enable_telemetry is False


@pytest.mark.unit
class TestTrackTelemetry:
    """Test _track_telemetry method."""

    def test_track_telemetry_skips_when_disabled(self):
        """Test telemetry is skipped when disabled."""
        mixin = TelemetryMixin()
        mixin.name = "test-workflow"
        mixin._enable_telemetry = False

        mock_tier = MagicMock()
        mock_tier.value = "CAPABLE"

        # Should not raise error
        mixin._track_telemetry(
            stage="test",
            tier=mock_tier,
            model="model-id",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=250,
        )

    def test_track_telemetry_skips_when_no_tracker(self):
        """Test telemetry is skipped when tracker not set."""
        mixin = TelemetryMixin()
        mixin.name = "test"
        mixin._telemetry_tracker = None

        mock_tier = MagicMock()
        mock_tier.value = "CAPABLE"

        mixin._track_telemetry(
            stage="test",
            tier=mock_tier,
            model="model",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=250,
        )

        # Should not crash

    def test_track_telemetry_calls_tracker(self):
        """Test telemetry tracker is called with correct data."""
        mixin = TelemetryMixin()
        mixin.name = "test-workflow"
        mixin._provider_str = "anthropic"

        mock_tracker = MagicMock()
        mixin._telemetry_tracker = mock_tracker

        mock_tier = MagicMock()
        mock_tier.value = "capable"

        mixin._track_telemetry(
            stage="analyze",
            tier=mock_tier,
            model="claude-3-5-haiku",
            cost=0.02,
            tokens={"input": 200, "output": 100},
            cache_hit=True,
            cache_type="semantic",
            duration_ms=500,
        )

        mock_tracker.track_llm_call.assert_called_once_with(
            workflow="test-workflow",
            stage="analyze",
            tier="CAPABLE",
            model="claude-3-5-haiku",
            provider="anthropic",
            cost=0.02,
            tokens={"input": 200, "output": 100},
            cache_hit=True,
            cache_type="semantic",
            duration_ms=500,
            prompt_cache_hit=False,
            prompt_cache_creation_tokens=0,
            prompt_cache_read_tokens=0,
        )

    def test_track_telemetry_handles_string_tier(self):
        """Test tracking handles tier as string."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_tracker = MagicMock()
        mixin._telemetry_tracker = mock_tracker

        mixin._track_telemetry(
            stage="stage1",
            tier="cheap",  # String instead of enum
            model="model",
            cost=0.01,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        # Should uppercase the string
        call_args = mock_tracker.track_llm_call.call_args[1]
        assert call_args["tier"] == "CHEAP"

    def test_track_telemetry_handles_tracker_error(self):
        """Test tracking handles tracker errors gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_tracker = MagicMock()
        mock_tracker.track_llm_call.side_effect = ValueError("Tracker error")
        mixin._telemetry_tracker = mock_tracker

        mock_tier = MagicMock()
        mock_tier.value = "capable"

        # Should not raise error
        mixin._track_telemetry(
            stage="test",
            tier=mock_tier,
            model="model",
            cost=0.01,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

    def test_track_telemetry_handles_os_error(self):
        """Test tracking handles file system errors gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_tracker = MagicMock()
        mock_tracker.track_llm_call.side_effect = OSError("Disk full")
        mixin._telemetry_tracker = mock_tracker

        mock_tier = MagicMock()
        mock_tier.value = "capable"

        # Should not raise error
        mixin._track_telemetry(
            stage="test",
            tier=mock_tier,
            model="model",
            cost=0.01,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )


@pytest.mark.unit
class TestEmitCallTelemetry:
    """Test _emit_call_telemetry method."""

    @patch("attune.workflows.telemetry_mixin.uuid.uuid4")
    @patch("attune.workflows.telemetry_mixin.datetime")
    @patch("attune.models.LLMCallRecord")
    def test_emit_call_telemetry_creates_record(self, mock_record_class, mock_datetime, mock_uuid):
        """Test call telemetry creates LLMCallRecord."""
        mixin = TelemetryMixin()
        mixin.name = "test-workflow"
        mixin._provider_str = "anthropic"
        mixin._run_id = "run-123"

        mock_backend = MagicMock()
        mixin._telemetry_backend = mock_backend

        mock_uuid.return_value = "call-456"
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2026-01-31T10:00:00"
        mock_datetime.now.return_value = mock_now

        mixin._emit_call_telemetry(
            step_name="step1",
            task_type="analyze",
            tier="capable",
            model_id="claude-3",
            input_tokens=100,
            output_tokens=50,
            cost=0.015,
            latency_ms=250,
            success=True,
            error_message=None,
            fallback_used=False,
        )

        mock_record_class.assert_called_once_with(
            call_id="call-456",
            timestamp="2026-01-31T10:00:00",
            workflow_name="test-workflow",
            step_name="step1",
            task_type="analyze",
            provider="anthropic",
            tier="capable",
            model_id="claude-3",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.015,
            latency_ms=250,
            success=True,
            error_message=None,
            fallback_used=False,
            metadata={"run_id": "run-123"},
        )

    @patch("attune.models.LLMCallRecord")
    def test_emit_call_telemetry_logs_to_backend(self, mock_record_class):
        """Test call telemetry is logged to backend."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_backend = MagicMock()
        mixin._telemetry_backend = mock_backend

        mock_record = MagicMock()
        mock_record_class.return_value = mock_record

        mixin._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )

        mock_backend.log_call.assert_called_once_with(mock_record)

    def test_emit_call_telemetry_handles_no_backend(self):
        """Test call telemetry handles missing backend gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"
        mixin._telemetry_backend = None

        # Should not raise error
        mixin._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )

    @patch("attune.models.LLMCallRecord")
    def test_emit_call_telemetry_handles_backend_error(self, mock_record_class):
        """Test call telemetry handles backend errors gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = ValueError("Backend error")
        mixin._telemetry_backend = mock_backend

        # Should not raise error
        mixin._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )

    @patch("attune.models.LLMCallRecord")
    def test_emit_call_telemetry_handles_os_error(self, mock_record_class):
        """Test call telemetry handles file system errors."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = OSError("Disk error")
        mixin._telemetry_backend = mock_backend

        # Should not raise error
        mixin._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )


@pytest.mark.unit
class TestEmitWorkflowTelemetry:
    """Test _emit_workflow_telemetry method."""

    @patch("attune.models.WorkflowRunRecord")
    @patch("attune.models.WorkflowStageRecord")
    def test_emit_workflow_telemetry_creates_records(self, mock_stage_record, mock_run_record):
        """Test workflow telemetry creates WorkflowRunRecord."""
        mixin = TelemetryMixin()
        mixin.name = "test-workflow"
        mixin._provider_str = "anthropic"
        mixin._run_id = "run-789"

        mock_backend = MagicMock()
        mixin._telemetry_backend = mock_backend

        # Mock workflow result
        mock_result = MagicMock()
        mock_result.started_at = datetime(2026, 1, 31, 10, 0, 0)
        mock_result.completed_at = datetime(2026, 1, 31, 10, 1, 0)
        mock_result.cost_report = MagicMock(
            total_cost=0.05,
            baseline_cost=0.10,
            savings=0.05,
            savings_percent=50.0,
            by_tier={"cheap": 0.01, "capable": 0.04},
        )
        mock_result.total_duration_ms = 60000
        mock_result.success = True
        mock_result.error = None

        # Mock stages
        mock_stage1 = MagicMock()
        mock_stage1.name = "stage1"
        mock_stage1.tier = MagicMock(value="cheap")
        mock_stage1.input_tokens = 100
        mock_stage1.output_tokens = 50
        mock_stage1.cost = 0.01
        mock_stage1.duration_ms = 200
        mock_stage1.skipped = False

        mock_result.stages = [mock_stage1]

        mixin.get_model_for_tier = MagicMock(return_value="claude-3-haiku")

        mixin._emit_workflow_telemetry(mock_result)

        # Verify WorkflowRunRecord was created
        assert mock_run_record.called

    def test_emit_workflow_telemetry_handles_no_backend(self):
        """Test workflow telemetry handles missing backend gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"
        mixin._telemetry_backend = None

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.cost_report = MagicMock(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
            by_tier={},
        )

        # Should not raise error
        mixin._emit_workflow_telemetry(mock_result)

    @patch("attune.models.WorkflowRunRecord")
    def test_emit_workflow_telemetry_handles_backend_error(self, mock_run_record):
        """Test workflow telemetry handles backend errors gracefully."""
        mixin = TelemetryMixin()
        mixin.name = "test"

        mock_backend = MagicMock()
        mock_backend.log_workflow.side_effect = ValueError("Backend error")
        mixin._telemetry_backend = mock_backend

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.cost_report = MagicMock(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
            by_tier={},
        )
        mock_result.total_duration_ms = 1000
        mock_result.success = True
        mock_result.error = None

        # Should not raise error
        mixin._emit_workflow_telemetry(mock_result)

    @patch("attune.models.WorkflowRunRecord")
    def test_emit_workflow_telemetry_handles_os_error(self, mock_run_record):
        """log_workflow raising OSError is logged and swallowed (lines 270-272)."""
        mixin = TelemetryMixin()
        mixin.name = "test"
        mock_backend = MagicMock()
        mock_backend.log_workflow.side_effect = OSError("Disk full")
        mixin._telemetry_backend = mock_backend

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.cost_report = MagicMock(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
            by_tier={},
        )
        mock_result.total_duration_ms = 1
        mock_result.success = True
        mock_result.error = None

        mixin._emit_workflow_telemetry(mock_result)  # must not raise

    @patch("attune.models.WorkflowRunRecord")
    def test_emit_workflow_telemetry_handles_generic_exception(self, mock_run_record):
        """log_workflow raising arbitrary Exception is caught at the bare-except (lines 273-275)."""
        mixin = TelemetryMixin()
        mixin.name = "test"
        mock_backend = MagicMock()
        # RuntimeError is NOT in (AttributeError, ValueError, TypeError) and NOT OSError —
        # so it must hit the catch-all bare-except handler.
        mock_backend.log_workflow.side_effect = RuntimeError("unexpected")
        mixin._telemetry_backend = mock_backend

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.cost_report = MagicMock(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
            by_tier={},
        )
        mock_result.total_duration_ms = 1
        mock_result.success = True
        mock_result.error = None

        mixin._emit_workflow_telemetry(mock_result)  # must not raise


@pytest.mark.unit
class TestInitTelemetryUnavailable:
    """Cover the branch where TELEMETRY_AVAILABLE is False (branch 83->exit)."""

    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", False)
    @patch("attune.workflows.telemetry_mixin.UsageTracker", None)
    def test_init_telemetry_skips_tracker_when_unavailable(self):
        mixin = TelemetryMixin()
        mixin.name = "test"
        mixin._init_telemetry(telemetry_backend=MagicMock())
        # Tracker stays None because availability check short-circuited
        assert mixin._telemetry_tracker is None
        # _enable_telemetry stays True (set before the check); the if-block exits early
        assert mixin._enable_telemetry is True


@pytest.mark.unit
class TestEmitCallTelemetryGenericException:
    """Cover the bare-except branch in _emit_call_telemetry (lines 212-214)."""

    @patch("attune.models.LLMCallRecord")
    def test_emit_call_telemetry_handles_generic_exception(self, mock_record_class):
        mixin = TelemetryMixin()
        mixin.name = "test"
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = RuntimeError("unexpected")
        mixin._telemetry_backend = mock_backend

        mixin._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )  # must not raise


@pytest.mark.unit
class TestGenerateRunId:
    """Test _generate_run_id method."""

    @patch("attune.workflows.telemetry_mixin.uuid.uuid4")
    def test_generate_run_id_creates_uuid(self, mock_uuid):
        """Test run ID generation creates UUID."""
        mixin = TelemetryMixin()

        mock_uuid.return_value = "test-uuid-123"

        run_id = mixin._generate_run_id()

        assert run_id == "test-uuid-123"
        assert mixin._run_id == "test-uuid-123"

    def test_generate_run_id_returns_string(self):
        """Test run ID is a string."""
        mixin = TelemetryMixin()

        run_id = mixin._generate_run_id()

        assert isinstance(run_id, str)
        assert len(run_id) > 0

    def test_generate_run_id_sets_internal_run_id(self):
        """Test run ID is stored internally."""
        mixin = TelemetryMixin()

        run_id = mixin._generate_run_id()

        assert mixin._run_id == run_id


@pytest.mark.unit
class TestIntegration:
    """Integration tests for TelemetryMixin."""

    @patch("attune.models.get_telemetry_store")
    @patch("attune.workflows.telemetry_mixin.TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.telemetry_mixin.UsageTracker")
    def test_full_telemetry_workflow(self, mock_tracker_class, mock_get_store):
        """Test complete telemetry workflow."""

        class TestWorkflow(TelemetryMixin):
            def __init__(self):
                self.name = "integration-test"
                self._provider_str = "anthropic"

        workflow = TestWorkflow()

        # Setup
        mock_backend = MagicMock()
        mock_get_store.return_value = mock_backend
        mock_tracker = MagicMock()
        mock_tracker_class.get_instance.return_value = mock_tracker

        workflow._init_telemetry()

        assert workflow._telemetry_backend is not None
        assert workflow._telemetry_tracker is not None

        # Generate run ID
        run_id = workflow._generate_run_id()
        assert workflow._run_id == run_id

        # Track telemetry
        mock_tier = MagicMock()
        mock_tier.value = "capable"

        workflow._track_telemetry(
            stage="test",
            tier=mock_tier,
            model="model",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=250,
        )

        mock_tracker.track_llm_call.assert_called_once()
