"""Unit tests for OTEL backend

Tests the OpenTelemetry backend for LLM telemetry export.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Check if opentelemetry is available before importing OTELBackend
# OTELBackend's _check_otel_installed() uses importlib.util.find_spec which can raise
_otel_available = False
try:
    # Try to import opentelemetry to check availability
    import opentelemetry  # noqa: F401

    _otel_available = True
except (ImportError, ModuleNotFoundError):
    pass

if not _otel_available:
    pytest.skip("opentelemetry not installed (optional dependency)", allow_module_level=True)

from attune.models.telemetry import (  # noqa: E402
    LLMCallRecord,
    WorkflowRunRecord,
    WorkflowStageRecord,
)
from attune.monitoring.otel_backend import OTELBackend  # noqa: E402


@pytest.mark.unit
class TestOTELBackendInitialization:
    """Test OTEL backend initialization and configuration."""

    def test_default_endpoint_detection(self):
        """Test that backend detects default localhost endpoint."""
        backend = OTELBackend()

        assert backend.endpoint == "http://localhost:4317"
        assert backend.batch_size == 10
        assert backend.retry_count == 3

    def test_custom_endpoint(self):
        """Test initialization with custom endpoint."""
        backend = OTELBackend(endpoint="http://custom:4318")

        assert backend.endpoint == "http://custom:4318"

    def test_custom_batch_size(self):
        """Test initialization with custom batch size."""
        backend = OTELBackend(batch_size=50)

        assert backend.batch_size == 50

    def test_environment_variable_endpoint(self):
        """Test that EMPATHY_OTEL_ENDPOINT env var is used."""
        with patch.dict(os.environ, {"EMPATHY_OTEL_ENDPOINT": "http://env:4317"}):
            backend = OTELBackend()

            assert backend.endpoint == "http://env:4317"

    def test_attune_otel_endpoint_env(self):
        """Test that ATTUNE_OTEL_ENDPOINT env var is used."""
        with patch.dict(os.environ, {"ATTUNE_OTEL_ENDPOINT": "http://attune:4317"}):
            backend = OTELBackend()
            assert backend.endpoint == "http://attune:4317"

    def test_attune_otel_endpoint_takes_precedence(self):
        """Test ATTUNE_ wins when both ATTUNE_ and EMPATHY_ are set."""
        env = {
            "ATTUNE_OTEL_ENDPOINT": "http://attune:4317",
            "EMPATHY_OTEL_ENDPOINT": "http://empathy:4317",
        }
        with patch.dict(os.environ, env):
            backend = OTELBackend()
            assert backend.endpoint == "http://attune:4317"

    @pytest.mark.xfail(
        reason="Test assumes OTEL not installed but it may be present in the environment",
        strict=False,
    )
    def test_otel_not_installed(self):
        """Test graceful handling when OTEL dependencies not installed."""
        backend = OTELBackend()

        # Should initialize even without OTEL installed
        assert backend is not None
        assert backend._otel_available is False

    def test_collector_not_available(self):
        """Test that backend handles unavailable collector gracefully."""
        backend = OTELBackend()

        # Collector not running on localhost:4317
        assert backend.is_available() is False


@pytest.mark.unit
class TestOTELBackendPortChecking:
    """Test port availability checking."""

    def test_is_port_open_localhost_closed(self):
        """Test checking closed port returns False."""
        backend = OTELBackend()

        # Port 9999 should not be open
        assert backend._is_port_open("localhost", 9999, timeout=0.1) is False

    def test_is_port_open_invalid_host(self):
        """Test checking invalid host returns False."""
        backend = OTELBackend()

        assert backend._is_port_open("invalid.host.example", 4317, timeout=0.1) is False

    def test_check_availability_no_endpoint(self):
        """Test availability check with no endpoint."""
        backend = OTELBackend()
        backend.endpoint = None

        assert backend._check_availability() is False

    def test_check_availability_invalid_endpoint(self):
        """Test availability check with malformed endpoint."""
        backend = OTELBackend(endpoint="not-a-url")

        assert backend._check_availability() is False


@pytest.mark.unit
class TestOTELBackendLogging:
    """Test LLM call and workflow logging."""

    def test_log_call_when_unavailable(self):
        """Test that log_call handles unavailable backend gracefully."""
        backend = OTELBackend()

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

    def test_log_workflow_when_unavailable(self):
        """Test that log_workflow handles unavailable backend gracefully."""
        backend = OTELBackend()

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
                )
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

        # Should not raise exception
        backend.log_workflow(workflow_record)

    @patch("attune.monitoring.otel_backend.OTELBackend._check_otel_installed")
    @patch("attune.monitoring.otel_backend.OTELBackend._check_availability")
    def test_log_call_with_mocked_otel(self, mock_availability, mock_otel_installed):
        """Test log_call with mocked OTEL availability."""
        mock_otel_installed.return_value = True
        mock_availability.return_value = True

        # Mock the tracer
        with patch("attune.monitoring.otel_backend.OTELBackend._init_otel"):
            backend = OTELBackend()
            backend._otel_available = True
            backend._available = True
            backend.tracer = MagicMock()

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

            # Should call tracer
            backend.log_call(call_record)
            backend.tracer.start_as_current_span.assert_called_once()

    def test_flush_when_unavailable(self):
        """Test that flush handles unavailable backend gracefully."""
        backend = OTELBackend()

        # Should not raise exception
        backend.flush()


@pytest.mark.unit
class TestOTELBackendErrorHandling:
    """Test error handling in OTEL backend."""

    def test_log_call_with_error_record(self):
        """Test logging a failed LLM call."""
        backend = OTELBackend()

        call_record = LLMCallRecord(
            call_id="test_001",
            timestamp="2026-01-05T10:00:00Z",
            provider="anthropic",
            model_id="claude-sonnet-4",
            tier="capable",
            task_type="test",
            input_tokens=100,
            output_tokens=0,
            estimated_cost=0.0,
            latency_ms=500,
            success=False,
            error_type="RateLimitError",
            error_message="Rate limit exceeded",
        )

        # Should not raise exception
        backend.log_call(call_record)

    def test_log_call_with_fallback(self):
        """Test logging a call that used fallback."""
        backend = OTELBackend()

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
            fallback_used=True,
            original_provider="openai",
            original_model="gpt-4o",
        )

        # Should not raise exception
        backend.log_call(call_record)

    def test_log_workflow_with_skipped_stage(self):
        """Test logging workflow with skipped stage."""
        backend = OTELBackend()

        workflow_record = WorkflowRunRecord(
            run_id="test_run",
            workflow_name="test",
            started_at="2026-01-05T10:00:00Z",
            completed_at="2026-01-05T10:01:00Z",
            stages=[
                WorkflowStageRecord(
                    stage_name="skipped_stage",
                    tier="capable",
                    model_id="claude-sonnet-4",
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    latency_ms=0,
                    success=True,
                    skipped=True,
                    skip_reason="Cache hit",
                )
            ],
            total_input_tokens=0,
            total_output_tokens=0,
            total_cost=0.0,
            baseline_cost=0.05,
            savings=0.05,
            savings_percent=100.0,
            total_duration_ms=100,
            success=True,
            providers_used=[],
            tiers_used=[],
        )

        # Should not raise exception
        backend.log_workflow(workflow_record)

    def test_log_workflow_with_stage_error(self):
        """Test logging workflow with failed stage."""
        backend = OTELBackend()

        workflow_record = WorkflowRunRecord(
            run_id="test_run",
            workflow_name="test",
            started_at="2026-01-05T10:00:00Z",
            completed_at="2026-01-05T10:01:00Z",
            stages=[
                WorkflowStageRecord(
                    stage_name="failed_stage",
                    tier="capable",
                    model_id="claude-sonnet-4",
                    input_tokens=100,
                    output_tokens=0,
                    cost=0.0,
                    latency_ms=500,
                    success=False,
                    skipped=False,
                    error="API timeout",
                )
            ],
            total_input_tokens=100,
            total_output_tokens=0,
            total_cost=0.0,
            baseline_cost=0.05,
            savings=0.0,
            savings_percent=0.0,
            total_duration_ms=500,
            success=False,
            error="Stage failed: failed_stage",
            providers_used=["anthropic"],
            tiers_used=["capable"],
        )

        # Should not raise exception
        backend.log_workflow(workflow_record)
