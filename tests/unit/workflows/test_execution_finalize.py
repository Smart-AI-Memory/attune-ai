"""Tests for execution_finalize module.

Tests _classify_error, _update_routing_record, and ExecutionFinalizeMixin.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.workflows.execution_finalize import (
    ExecutionFinalizeMixin,
    _classify_error,
    _update_routing_record,
)

# ---------------------------------------------------------------------------
# Tests for _classify_error
# ---------------------------------------------------------------------------


class TestClassifyError:
    """Tests for the _classify_error function."""

    def test_timeout_error(self):
        """Timeout errors are classified as transient."""
        error_type, transient = _classify_error("Connection timed out after 30s")

        assert error_type == "timeout"
        assert transient is True

    def test_timeout_variant(self):
        """'timeout' keyword also matches."""
        error_type, transient = _classify_error("Request timeout")

        assert error_type == "timeout"
        assert transient is True

    def test_config_error(self):
        """Configuration errors are non-transient."""
        error_type, transient = _classify_error("Invalid configuration for provider")

        assert error_type == "config"
        assert transient is False

    def test_api_error(self):
        """API errors are transient."""
        error_type, transient = _classify_error("API rate limit exceeded")

        assert error_type == "provider"
        assert transient is True

    def test_rate_limit_error(self):
        """Rate limit errors are transient."""
        error_type, transient = _classify_error("Rate limit reached")

        assert error_type == "provider"
        assert transient is True

    def test_quota_error(self):
        """Quota errors are transient."""
        error_type, transient = _classify_error("Quota exceeded for model")

        assert error_type == "provider"
        assert transient is True

    def test_validation_error(self):
        """Validation errors are non-transient."""
        error_type, transient = _classify_error("Validation failed: invalid input")

        assert error_type == "validation"
        assert transient is False

    def test_generic_error(self):
        """Unknown errors default to runtime, non-transient."""
        error_type, transient = _classify_error("Something completely unexpected")

        assert error_type == "runtime"
        assert transient is False

    def test_case_insensitive(self):
        """Classification is case-insensitive."""
        error_type, _ = _classify_error("TIMEOUT ERROR")

        assert error_type == "timeout"


# ---------------------------------------------------------------------------
# Tests for _update_routing_record
# ---------------------------------------------------------------------------


class TestUpdateRoutingRecord:
    """Tests for the _update_routing_record function."""

    def _make_record(self):
        """Create a minimal routing record mock."""
        record = MagicMock()
        record.status = None
        record.completed_at = None
        record.success = None
        record.actual_cost = None
        record.error_type = None
        record.error_message = None
        return record

    def _make_stage(self, cost=0.01):
        """Create a minimal stage mock."""
        stage = MagicMock()
        stage.cost = cost
        return stage

    def test_successful_result(self):
        """Successful result updates record correctly."""
        record = self._make_record()
        workflow = MagicMock()
        workflow._telemetry_backend = None

        result = MagicMock()
        result.success = True
        result.error = None
        result.stages = [self._make_stage(0.01), self._make_stage(0.02)]

        _update_routing_record(workflow, record, result)

        assert record.status == "completed"
        assert record.success is True
        assert record.actual_cost == pytest.approx(0.03)

    def test_failed_result(self):
        """Failed result sets error fields."""
        record = self._make_record()
        workflow = MagicMock()
        workflow._telemetry_backend = None

        result = MagicMock()
        result.success = False
        result.error = "Timeout occurred"
        result.error_type = "timeout"
        result.stages = [self._make_stage(0.01)]

        _update_routing_record(workflow, record, result)

        assert record.status == "failed"
        assert record.success is False
        assert record.error_type == "timeout"
        assert record.error_message == "Timeout occurred"

    def test_telemetry_logged(self):
        """Telemetry backend is called when available."""
        record = self._make_record()
        workflow = MagicMock()

        result = MagicMock()
        result.success = True
        result.error = None
        result.stages = []

        _update_routing_record(workflow, record, result)

        workflow._telemetry_backend.log_task_routing.assert_called_once_with(record)

    def test_telemetry_failure_ignored(self):
        """Telemetry logging failure doesn't crash."""
        record = self._make_record()
        workflow = MagicMock()
        workflow._telemetry_backend.log_task_routing.side_effect = Exception("fail")

        result = MagicMock()
        result.success = True
        result.error = None
        result.stages = []

        # Should not raise
        _update_routing_record(workflow, record, result)


# ---------------------------------------------------------------------------
# Tests for ExecutionFinalizeMixin._save_tier_progression
# ---------------------------------------------------------------------------


class TestSaveTierProgression:
    """Tests for ExecutionFinalizeMixin._save_tier_progression."""

    def _make_mixin(self, enable_tracking=False, enable_fallback=False):
        """Create a mixin instance with required attributes."""
        obj = ExecutionFinalizeMixin()
        obj._enable_tier_tracking = enable_tracking
        obj._tier_tracker = MagicMock() if enable_tracking else None
        obj._enable_tier_fallback = enable_fallback
        obj._tier_progression = [{"tier": "cheap", "success": True}]
        obj.name = "code-review"
        return obj

    def test_skip_when_disabled(self):
        """Does nothing when tier tracking is disabled."""
        obj = self._make_mixin(enable_tracking=False)
        result = MagicMock()

        obj._save_tier_progression({}, result)

        # No tracker to call
        assert obj._tier_tracker is None

    def test_saves_with_tracking_enabled(self):
        """Calls tracker.save_progression when enabled."""
        obj = self._make_mixin(enable_tracking=True)
        result = MagicMock()

        obj._save_tier_progression({"path": "src/foo.py"}, result)

        obj._tier_tracker.save_progression.assert_called_once()

    def test_maps_workflow_to_bug_type(self):
        """Workflow name maps to expected bug_type."""
        obj = self._make_mixin(enable_tracking=True)
        obj.name = "security-audit"
        result = MagicMock()

        obj._save_tier_progression({}, result)

        call_kwargs = obj._tier_tracker.save_progression.call_args[1]
        assert call_kwargs["bug_type"] == "security_issue"

    def test_unknown_workflow_maps_to_default(self):
        """Unknown workflow name maps to 'workflow_run'."""
        obj = self._make_mixin(enable_tracking=True)
        obj.name = "custom-workflow"
        result = MagicMock()

        obj._save_tier_progression({}, result)

        call_kwargs = obj._tier_tracker.save_progression.call_args[1]
        assert call_kwargs["bug_type"] == "workflow_run"

    def test_exception_handled_gracefully(self):
        """Tracker errors don't crash."""
        obj = self._make_mixin(enable_tracking=True)
        obj._tier_tracker.save_progression.side_effect = Exception("fail")
        result = MagicMock()

        # Should not raise
        obj._save_tier_progression({}, result)
