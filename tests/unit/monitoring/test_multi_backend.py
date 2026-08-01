"""Unit tests for multi-backend support

Tests the multi-backend composite pattern for simultaneous JSONL + OTEL logging.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import attune.monitoring.otel_backend as otel_backend_module
from attune.models.telemetry import (
    LLMCallRecord,
    TelemetryStore,
    WorkflowRunRecord,
    WorkflowStageRecord,
)
from attune.monitoring.multi_backend import MultiBackend, get_multi_backend, reset_multi_backend
from attune.monitoring.otel_backend import OTELBackend


def _make_workflow_record() -> WorkflowRunRecord:
    """Build a minimal WorkflowRunRecord for logging tests."""
    return WorkflowRunRecord(
        run_id="test_run",
        workflow_name="test",
        started_at="2026-01-05T10:00:00Z",
        completed_at="2026-01-05T10:01:00Z",
        stages=[
            WorkflowStageRecord(
                stage_name="test",
                tier="capable",
                model_id="claude-sonnet-4",
                input_tokens=100,
                output_tokens=50,
                cost=0.01,
                latency_ms=1000,
                success=True,
                skipped=False,
            ),
        ],
        total_input_tokens=100,
        total_output_tokens=50,
        total_cost=0.01,
        baseline_cost=0.05,
        savings=0.04,
        savings_percent=80.0,
        total_duration_ms=60000,
        success=True,
        providers_used=["anthropic"],
        tiers_used=["capable"],
    )


@pytest.mark.unit
class TestMultiBackendInitialization:
    """Test multi-backend initialization."""

    def test_empty_initialization(self):
        """Test creating multi-backend with no backends."""
        backend = MultiBackend()

        assert len(backend.backends) == 0
        assert len(backend) == 0

    def test_initialization_with_backends(self):
        """Test creating multi-backend with backend list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            backend = MultiBackend(backends=[store])

            assert len(backend.backends) == 1
            assert len(backend) == 1

    def test_from_config_creates_jsonl_backend(self):
        """Test that from_config creates JSONL backend by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = MultiBackend.from_config(tmpdir)

            assert len(backend.backends) >= 1
            assert "TelemetryStore" in backend.get_active_backends()

    def test_from_config_with_otel_import_error(self):
        """Test that from_config handles OTEL import error gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # OTEL may not be installed, which is fine
            backend = MultiBackend.from_config(tmpdir)

            # Should at least have JSONL backend
            assert len(backend.backends) >= 1
            assert "TelemetryStore" in backend.get_active_backends()

    def test_from_config_without_otel_collector(self):
        """Test from_config when OTEL collector is not running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = MultiBackend.from_config(tmpdir)

            # OTEL backend won't be added if collector isn't available
            # Should have at least JSONL
            assert "TelemetryStore" in backend.get_active_backends()


@pytest.mark.unit
class TestMultiBackendManagement:
    """Test backend addition and removal."""

    def test_add_backend(self):
        """Test adding a backend to multi-backend."""
        backend = MultiBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            backend.add_backend(store)

            assert len(backend.backends) == 1

    def test_add_invalid_backend_raises_error(self):
        """Test that adding non-backend raises TypeError."""
        backend = MultiBackend()

        with pytest.raises(TypeError, match="must implement TelemetryBackend protocol"):
            backend.add_backend("not a backend")  # type: ignore

    def test_remove_backend(self):
        """Test removing a backend from multi-backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            backend = MultiBackend(backends=[store])

            assert len(backend.backends) == 1

            backend.remove_backend(store)

            assert len(backend.backends) == 0

    def test_remove_nonexistent_backend(self):
        """Test removing backend that doesn't exist."""
        backend = MultiBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)

            # Should not raise error
            backend.remove_backend(store)


@pytest.mark.unit
class TestMultiBackendLogging:
    """Test logging to multiple backends."""

    def test_log_call_to_all_backends(self):
        """Test that log_call sends to all backends."""
        mock_backend1 = MagicMock()
        mock_backend2 = MagicMock()
        backend = MultiBackend(backends=[mock_backend1, mock_backend2])

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        backend.log_call(call_record)

        mock_backend1.log_call.assert_called_once_with(call_record)
        mock_backend2.log_call.assert_called_once_with(call_record)

    def test_log_workflow_to_all_backends(self):
        """Test that log_workflow sends to all backends."""
        mock_backend1 = MagicMock()
        mock_backend2 = MagicMock()
        backend = MultiBackend(backends=[mock_backend1, mock_backend2])

        workflow_record = WorkflowRunRecord(
            run_id="test_run",
            workflow_name="test",
            started_at="2026-01-05T10:00:00Z",
            completed_at="2026-01-05T10:01:00Z",
            stages=[
                WorkflowStageRecord(
                    stage_name="test",
                    tier="capable",
                    model_id="claude-sonnet-4",
                    input_tokens=100,
                    output_tokens=50,
                    cost=0.01,
                    latency_ms=1000,
                    success=True,
                    skipped=False,
                ),
            ],
            total_input_tokens=100,
            total_output_tokens=50,
            total_cost=0.01,
            baseline_cost=0.05,
            savings=0.04,
            savings_percent=80.0,
            total_duration_ms=60000,
            success=True,
            providers_used=["anthropic"],
            tiers_used=["capable"],
        )

        backend.log_workflow(workflow_record)

        mock_backend1.log_workflow.assert_called_once_with(workflow_record)
        mock_backend2.log_workflow.assert_called_once_with(workflow_record)


@pytest.mark.unit
class TestMultiBackendErrorHandling:
    """Test graceful error handling."""

    def test_log_call_continues_on_backend_failure(self):
        """Test that failure in one backend doesn't affect others."""
        mock_backend1 = MagicMock()
        mock_backend1.log_call.side_effect = Exception("Backend 1 failed")

        mock_backend2 = MagicMock()

        backend = MultiBackend(backends=[mock_backend1, mock_backend2])

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        # Should not raise exception
        backend.log_call(call_record)

        # Backend 2 should still be called
        mock_backend2.log_call.assert_called_once_with(call_record)

        # Backend 1 should be marked as failed
        assert 0 in backend._failed_backends

    def test_failed_backend_skipped_on_subsequent_calls(self):
        """Test that failed backends are skipped on subsequent calls."""
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = Exception("Failed")

        backend = MultiBackend(backends=[mock_backend])

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        # First call - backend fails
        backend.log_call(call_record)
        assert mock_backend.log_call.call_count == 1

        # Second call - backend should be skipped
        backend.log_call(call_record)
        assert mock_backend.log_call.call_count == 1  # Not called again

    def test_reset_failures_retries_failed_backends(self):
        """Test that reset_failures allows retrying failed backends."""
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = [Exception("Failed"), None]

        backend = MultiBackend(backends=[mock_backend])

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        # First call - backend fails
        backend.log_call(call_record)
        assert 0 in backend._failed_backends

        # Reset failures
        backend.reset_failures()
        assert len(backend._failed_backends) == 0

        # Second call - backend should be tried again
        backend.log_call(call_record)
        assert mock_backend.log_call.call_count == 2


@pytest.mark.unit
class TestMultiBackendStatus:
    """Test backend status tracking."""

    def test_get_active_backends(self):
        """Test getting list of active backends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            backend = MultiBackend(backends=[store])

            active = backend.get_active_backends()

            assert "TelemetryStore" in active

    def test_get_failed_backends(self):
        """Test getting list of failed backends."""
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = Exception("Failed")

        backend = MultiBackend(backends=[mock_backend])

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        backend.log_call(call_record)

        failed = backend.get_failed_backends()
        assert "MagicMock" in failed

    def test_len_returns_active_backend_count(self):
        """Test that len() returns number of active backends."""
        mock_backend1 = MagicMock()
        mock_backend1.log_call.side_effect = Exception("Failed")
        mock_backend2 = MagicMock()

        backend = MultiBackend(backends=[mock_backend1, mock_backend2])

        assert len(backend) == 2

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )

        backend.log_call(call_record)

        # One failed, one active
        assert len(backend) == 1

    def test_repr(self):
        """Test string representation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            backend = MultiBackend(backends=[store])

            repr_str = repr(backend)

            assert "MultiBackend" in repr_str
            assert "active=" in repr_str

    def test_repr_includes_failed_backends(self):
        """repr() must also surface failed backends, not just active ones."""
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = Exception("Failed")

        backend = MultiBackend(backends=[mock_backend])
        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.01,
            latency_ms=1000,
            success=True,
        )
        backend.log_call(call_record)

        repr_str = repr(backend)

        assert "failed=" in repr_str
        assert "MagicMock" in repr_str


@pytest.mark.unit
class TestMultiBackendFlush:
    """Test flushing backends."""

    def test_flush_calls_backend_flush(self):
        """Test that flush calls flush on backends that support it."""
        mock_backend = MagicMock()
        mock_backend.flush = MagicMock()

        backend = MultiBackend(backends=[mock_backend])
        backend.flush()

        mock_backend.flush.assert_called_once()

    def test_flush_handles_backend_without_flush(self):
        """Test that flush handles backends without flush method."""
        mock_backend = MagicMock(spec=[])  # No flush method

        backend = MultiBackend(backends=[mock_backend])

        # Should not raise exception
        backend.flush()

    def test_flush_handles_flush_failure(self):
        """Test that flush handles backend flush failures gracefully."""
        mock_backend = MagicMock()
        mock_backend.flush.side_effect = Exception("Flush failed")

        backend = MultiBackend(backends=[mock_backend])

        # Should not raise exception
        backend.flush()


@pytest.mark.unit
class TestGlobalMultiBackend:
    """Test global multi-backend singleton."""

    def test_get_multi_backend_creates_instance(self):
        """Test that get_multi_backend creates a singleton instance."""
        # Reset global instance
        reset_multi_backend()

        with tempfile.TemporaryDirectory() as tmpdir:
            backend1 = get_multi_backend(tmpdir)
            backend2 = get_multi_backend(tmpdir)

            # Should be same instance
            assert backend1 is backend2

    def test_reset_multi_backend_clears_instance(self):
        """Test that reset_multi_backend creates new instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend1 = get_multi_backend(tmpdir)
            reset_multi_backend()
            backend2 = get_multi_backend(tmpdir)

            # Should be different instances
            assert backend1 is not backend2

    def test_reset_flushes_before_clearing(self):
        """Test that reset flushes data before clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = get_multi_backend(tmpdir)
            backend.flush = MagicMock()

            reset_multi_backend()

            backend.flush.assert_called_once()


@pytest.mark.unit
class TestFromConfigBackendIsolation:
    """A failure initializing one backend must not break from_config().

    Covers the JSONL-init except branch and every OTEL-detection branch
    (available, ImportError, and a generic init failure) that the happy-path
    tests above never trigger.
    """

    def test_jsonl_init_failure_is_isolated(self):
        """TelemetryStore() raising during from_config must not raise or
        prevent the OTEL branch from still being evaluated."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "attune.monitoring.multi_backend.TelemetryStore",
                side_effect=OSError("disk full"),
            ),
        ):
            backend = MultiBackend.from_config(tmpdir)

        # JSONL backend failed to construct, so it's simply absent - no crash.
        assert "TelemetryStore" not in backend.get_active_backends()

    def test_otel_backend_appended_when_available(self):
        """When OTELBackend.is_available() is True, it's added to backends."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(OTELBackend, "is_available", return_value=True),
        ):
            backend = MultiBackend.from_config(tmpdir)

        assert "OTELBackend" in backend.get_active_backends()

    def test_otel_import_error_is_isolated(self):
        """A missing attune.monitoring.otel_backend module (the shape of a
        missing optional dependency) must not break from_config()."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(sys.modules, {"attune.monitoring.otel_backend": None}),
        ):
            backend = MultiBackend.from_config(tmpdir)

        assert "OTELBackend" not in backend.get_active_backends()
        # JSONL backend still constructed fine.
        assert "TelemetryStore" in backend.get_active_backends()

    def test_otel_generic_init_failure_is_isolated(self):
        """A non-ImportError raised while constructing OTELBackend() must be
        caught and logged, not propagated."""

        class _BrokenOTELBackend:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("collector handshake failed")

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(otel_backend_module, "OTELBackend", _BrokenOTELBackend),
        ):
            backend = MultiBackend.from_config(tmpdir)

        assert "OTELBackend" not in backend.get_active_backends()
        assert "TelemetryStore" in backend.get_active_backends()


@pytest.mark.unit
class TestLogWorkflowErrorHandling:
    """log_workflow() must isolate per-backend failures the same way
    log_call() does - the happy-path tests above never fail a backend or
    skip a previously-failed one on a second call."""

    def test_log_workflow_continues_on_backend_failure(self):
        """A backend raising during log_workflow doesn't stop the others,
        and gets marked failed."""
        mock_backend1 = MagicMock()
        mock_backend1.log_workflow.side_effect = Exception("Workflow log failed")
        mock_backend2 = MagicMock()

        backend = MultiBackend(backends=[mock_backend1, mock_backend2])
        workflow_record = _make_workflow_record()

        backend.log_workflow(workflow_record)

        mock_backend2.log_workflow.assert_called_once_with(workflow_record)
        assert 0 in backend._failed_backends
        assert "MagicMock" in backend.get_failed_backends()

    def test_log_workflow_skips_previously_failed_backend(self):
        """A backend already marked failed is skipped on a later
        log_workflow() call without being invoked again."""
        mock_backend = MagicMock()
        mock_backend.log_workflow.side_effect = Exception("Failed")

        backend = MultiBackend(backends=[mock_backend])
        workflow_record = _make_workflow_record()

        # First call fails and marks the backend as failed.
        backend.log_workflow(workflow_record)
        assert mock_backend.log_workflow.call_count == 1

        # Second call must skip the failed backend entirely.
        backend.log_workflow(workflow_record)
        assert mock_backend.log_workflow.call_count == 1
