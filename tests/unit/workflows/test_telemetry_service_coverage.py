"""Tests for TelemetryService — covering init failures, emit methods.

Targets the uncovered lines: 27-29 (import failure), 89-94 (init errors),
152, 210, 213-215, 266-269 (emit error paths).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_backend():
    """Create a mock telemetry backend."""
    backend = MagicMock()
    backend.log_call = MagicMock()
    backend.log_workflow = MagicMock()
    return backend


@pytest.fixture
def service(mock_backend):
    """Create a TelemetryService with mocked backend."""
    from attune.workflows.services.telemetry_service import TelemetryService

    svc = TelemetryService("test-workflow", "anthropic", backend=mock_backend)
    return svc


class TestTelemetryServiceInit:
    """Test TelemetryService initialization paths."""

    def test_init_with_backend(self, mock_backend):
        """TelemetryService accepts a backend parameter."""
        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        assert svc._workflow_name == "wf"
        assert svc._backend is mock_backend

    @patch("attune.workflows.services.telemetry_service._TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.services.telemetry_service.UsageTracker")
    def test_init_tracker_os_error(self, mock_tracker_cls, mock_backend):
        """TelemetryService handles OSError during tracker init."""
        mock_tracker_cls.get_instance.side_effect = OSError("disk full")

        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        assert svc._enabled is False

    @patch("attune.workflows.services.telemetry_service._TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.services.telemetry_service.UsageTracker")
    def test_init_tracker_attribute_error(self, mock_tracker_cls, mock_backend):
        """TelemetryService handles AttributeError during tracker init."""
        mock_tracker_cls.get_instance.side_effect = AttributeError("bad config")

        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        assert svc._enabled is False

    @patch("attune.workflows.services.telemetry_service._TELEMETRY_AVAILABLE", True)
    @patch("attune.workflows.services.telemetry_service.UsageTracker")
    def test_init_tracker_permission_error(self, mock_tracker_cls, mock_backend):
        """TelemetryService handles PermissionError during tracker init."""
        mock_tracker_cls.get_instance.side_effect = PermissionError("no access")

        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        assert svc._enabled is False


class TestTelemetryServiceTrackCall:
    """Test track_call error paths."""

    def test_track_call_disabled(self, mock_backend):
        """track_call is a no-op when disabled."""
        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        svc._enabled = False
        # Should not raise
        svc.track_call(
            stage="test",
            tier=MagicMock(value="capable"),
            model="claude",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
        )

    def test_track_call_tracker_none(self, mock_backend):
        """track_call is a no-op when tracker is None."""
        from attune.workflows.services.telemetry_service import TelemetryService

        svc = TelemetryService("wf", "anthropic", backend=mock_backend)
        svc._enabled = True
        svc._tracker = None
        svc.track_call(
            stage="test",
            tier=MagicMock(value="capable"),
            model="claude",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
        )


class TestTelemetryServiceEmitCallRecord:
    """Test emit_call_record paths."""

    def test_emit_call_record_success(self, service, mock_backend):
        """emit_call_record logs to backend."""
        service.emit_call_record(
            step_name="analysis",
            task_type="review",
            tier="capable",
            model_id="claude-3-haiku",
            input_tokens=500,
            output_tokens=200,
            cost=0.01,
            latency_ms=1000,
        )
        mock_backend.log_call.assert_called_once()

    def test_emit_call_record_backend_attribute_error(self, service, mock_backend):
        """emit_call_record handles AttributeError from backend."""
        mock_backend.log_call.side_effect = AttributeError("missing method")
        # Should not raise
        service.emit_call_record(
            step_name="test",
            task_type="review",
            tier="capable",
            model_id="claude",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=500,
        )

    def test_emit_call_record_backend_os_error(self, service, mock_backend):
        """emit_call_record handles OSError from backend."""
        mock_backend.log_call.side_effect = OSError("disk full")
        service.emit_call_record(
            step_name="test",
            task_type="review",
            tier="capable",
            model_id="claude",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=500,
        )

    def test_emit_call_record_backend_unexpected_error(self, service, mock_backend):
        """emit_call_record handles unexpected errors from backend."""
        mock_backend.log_call.side_effect = RuntimeError("unexpected")
        service.emit_call_record(
            step_name="test",
            task_type="review",
            tier="capable",
            model_id="claude",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=500,
        )

    def test_emit_call_record_none_backend(self, service):
        """emit_call_record handles None backend."""
        service._backend = None
        service.emit_call_record(
            step_name="test",
            task_type="review",
            tier="capable",
            model_id="claude",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=500,
        )


class TestTelemetryServiceEmitWorkflowRecord:
    """Test emit_workflow_record paths."""

    def _make_mock_result(self):
        """Create a mock WorkflowResult."""
        stage = MagicMock()
        stage.name = "analysis"
        stage.tier = MagicMock(value="capable")
        stage.input_tokens = 500
        stage.output_tokens = 200
        stage.cost = 0.01
        stage.duration_ms = 1000
        stage.skipped = False
        stage.skip_reason = None

        result = MagicMock()
        result.stages = [stage]
        result.started_at = datetime.now()
        result.completed_at = datetime.now()
        result.cost_report = MagicMock(
            total_cost=0.01,
            baseline_cost=0.02,
            savings=0.01,
            savings_percent=50.0,
            by_tier={"capable": 0.01},
        )
        result.total_duration_ms = 1000
        result.success = True
        result.error = None
        return result

    def test_emit_workflow_record_success(self, service, mock_backend):
        """emit_workflow_record logs to backend."""
        result = self._make_mock_result()
        service.emit_workflow_record(result)
        mock_backend.log_workflow.assert_called_once()

    def test_emit_workflow_record_backend_attribute_error(self, service, mock_backend):
        """emit_workflow_record handles AttributeError from backend."""
        mock_backend.log_workflow.side_effect = AttributeError("bad")
        result = self._make_mock_result()
        service.emit_workflow_record(result)

    def test_emit_workflow_record_backend_os_error(self, service, mock_backend):
        """emit_workflow_record handles OSError from backend."""
        mock_backend.log_workflow.side_effect = OSError("disk full")
        result = self._make_mock_result()
        service.emit_workflow_record(result)

    def test_emit_workflow_record_unexpected_error(self, service, mock_backend):
        """emit_workflow_record handles unexpected errors from backend."""
        mock_backend.log_workflow.side_effect = RuntimeError("unexpected")
        result = self._make_mock_result()
        service.emit_workflow_record(result)

    def test_emit_workflow_record_none_backend(self, service):
        """emit_workflow_record handles None backend."""
        service._backend = None
        result = self._make_mock_result()
        service.emit_workflow_record(result)

    def test_emit_workflow_record_generates_run_id(self, service, mock_backend):
        """emit_workflow_record generates run_id if not set."""
        service._run_id = None
        result = self._make_mock_result()
        service.emit_workflow_record(result)
        mock_backend.log_workflow.assert_called_once()


class TestTelemetryServiceRunId:
    """Test run_id property and generation."""

    def test_run_id_initially_none(self, service):
        """run_id starts as None."""
        service._run_id = None
        assert service.run_id is None

    def test_generate_run_id(self, service):
        """generate_run_id sets and returns a UUID."""
        rid = service.generate_run_id()
        assert rid is not None
        assert service.run_id == rid
        assert len(rid) == 36  # UUID format
