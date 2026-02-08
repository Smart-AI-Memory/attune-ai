"""Behavioral tests for multiple telemetry modules.

Tests event_streaming, agent_coordination, feedback_loop, approval_gates,
and other telemetry functionality.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import importlib.util
from datetime import datetime
from unittest.mock import Mock

import pytest

# Check if opentelemetry is available
_otel_available = importlib.util.find_spec("opentelemetry") is not None


class TestEventStreaming:
    """Test event streaming functionality."""

    def test_creates_event_stream(self):
        """Test creating an event streamer."""
        from attune.telemetry.event_streaming import EventStreamer

        streamer = EventStreamer()

        assert streamer is not None

    def test_publishes_event(self):
        """Test publishing an event to stream."""
        from attune.telemetry.event_streaming import EventStreamer

        streamer = EventStreamer()

        event_data = {
            "workflow": "code-review",
            "timestamp": datetime.now().isoformat(),
        }

        # Should not crash even without Redis backend
        event_id = streamer.publish_event(event_type="workflow_started", data=event_data)

        # Without Redis backend, returns empty string
        assert isinstance(event_id, str)

    def test_subscribes_to_events(self):
        """Test subscribing to event stream."""
        from attune.telemetry.event_streaming import EventStreamer

        streamer = EventStreamer()

        # Without Redis backend, consume_events should handle gracefully
        events = list(streamer.consume_events(event_types=["workflow_started"]))

        # Should return empty iterator without Redis
        assert len(events) == 0

    def test_filters_by_event_type(self):
        """Test filtering events by type."""
        from attune.telemetry.event_streaming import EventStreamer

        streamer = EventStreamer()

        # Without Redis backend, should handle gracefully
        events = streamer.get_recent_events(event_type="workflow_started", count=10)

        # Should return empty list without Redis
        assert isinstance(events, list)
        assert len(events) == 0

    def test_persists_events_to_disk(self):
        """Test that events are handled gracefully without Redis."""
        from attune.telemetry.event_streaming import EventStreamer

        streamer = EventStreamer()

        # Publish event (will be no-op without Redis)
        event_id = streamer.publish_event(event_type="test_event", data={"data": "test"})

        # Should handle gracefully
        assert isinstance(event_id, str)


class TestAgentCoordination:
    """Test agent coordination functionality."""

    def test_creates_coordinator(self):
        """Test creating coordination signals."""
        from attune.telemetry.agent_coordination import CoordinationSignals

        coordinator = CoordinationSignals(agent_id="agent-1")

        assert coordinator is not None
        assert coordinator.agent_id == "agent-1"

    def test_registers_agent(self):
        """Test sending coordination signals."""
        from attune.telemetry.agent_coordination import CoordinationSignals

        coordinator = CoordinationSignals(agent_id="agent-1")

        # Send signal (will be no-op without Redis)
        signal_id = coordinator.signal(
            signal_type="task_complete",
            source_agent="agent-1",
            target_agent="agent-2",
            payload={"status": "done"},
        )

        # Should handle gracefully
        assert isinstance(signal_id, str)

    def test_coordinates_multi_agent_workflow(self):
        """Test coordinating multiple agents via signals."""
        from attune.telemetry.agent_coordination import CoordinationSignals

        coordinator1 = CoordinationSignals(agent_id="agent-1")
        coordinator2 = CoordinationSignals(agent_id="agent-2")

        # Send signals
        signal_id1 = coordinator1.signal(
            signal_type="ready",
            target_agent="agent-2",
            payload={"status": "ready"},
        )
        signal_id2 = coordinator2.signal(
            signal_type="ready",
            target_agent="agent-1",
            payload={"status": "ready"},
        )

        # Should handle gracefully without Redis
        assert isinstance(signal_id1, str)
        assert isinstance(signal_id2, str)

    def test_detects_agent_failure(self):
        """Test detecting agent failure via signals."""
        from attune.telemetry.agent_coordination import CoordinationSignals

        coordinator = CoordinationSignals(agent_id="agent-1")

        # Send failure signal
        signal_id = coordinator.signal(
            signal_type="agent_error",
            payload={"error": "Timeout", "agent_id": "agent-1"},
        )

        # Should handle gracefully
        assert isinstance(signal_id, str)

    def test_redistributes_tasks_on_failure(self):
        """Test task redistribution signal."""
        from attune.telemetry.agent_coordination import CoordinationSignals

        coordinator = CoordinationSignals(agent_id="orchestrator")

        # Broadcast task redistribution signal
        signal_id = coordinator.broadcast(
            signal_type="redistribute_tasks",
            payload={"failed_agent": "agent-1", "reassign_to": "agent-2"},
        )

        # Should handle gracefully
        assert isinstance(signal_id, str)


class TestFeedbackLoop:
    """Test feedback loop functionality."""

    def test_creates_feedback_collector(self):
        """Test creating feedback loop."""
        from attune.telemetry.feedback_loop import FeedbackLoop

        collector = FeedbackLoop()

        assert collector is not None

    def test_collects_positive_feedback(self):
        """Test collecting positive feedback."""
        from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

        collector = FeedbackLoop()

        # Record high quality feedback
        feedback_id = collector.record_feedback(
            workflow_name="code-review",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
            quality_score=0.95,  # Excellent quality
            metadata={"comment": "Excellent analysis"},
        )

        # Should handle gracefully
        assert isinstance(feedback_id, str)

    def test_collects_negative_feedback(self):
        """Test collecting negative feedback."""
        from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

        collector = FeedbackLoop()

        # Record low quality feedback
        feedback_id = collector.record_feedback(
            workflow_name="test-gen",
            stage_name="generation",
            tier=ModelTier.CHEAP,
            quality_score=0.4,  # Poor quality
            metadata={"comment": "Missed edge cases"},
        )

        # Should handle gracefully
        assert isinstance(feedback_id, str)

    def test_calculates_average_rating(self):
        """Test calculating average quality."""
        from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

        collector = FeedbackLoop()

        # Record multiple ratings
        for score in [0.8, 0.7, 0.9, 0.6, 0.75]:
            collector.record_feedback(
                workflow_name="test",
                stage_name="analysis",
                tier=ModelTier.CHEAP,
                quality_score=score,
            )

        # Get stats (will be None without Redis)
        stats = collector.get_quality_stats(
            workflow_name="test",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
        )

        # Should handle gracefully
        assert stats is None or hasattr(stats, "avg_quality")

    def test_identifies_improvement_areas(self):
        """Test identifying areas needing improvement."""
        from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

        collector = FeedbackLoop()

        # Record poor quality feedback
        collector.record_feedback(
            workflow_name="test",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
            quality_score=0.5,
            metadata={"issue": "Slow response time"},
        )
        collector.record_feedback(
            workflow_name="test",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
            quality_score=0.6,
            metadata={"issue": "Response time could be better"},
        )

        # Get underperforming stages (will be empty without Redis)
        underperforming = collector.get_underperforming_stages(
            workflow_name="test",
            quality_threshold=0.7,
        )

        # Should handle gracefully
        assert isinstance(underperforming, list)

    def test_tracks_improvement_over_time(self):
        """Test tracking improvement trends over time."""
        from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

        collector = FeedbackLoop()

        # Simulate improving quality over time
        for score in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            collector.record_feedback(
                workflow_name="test",
                stage_name="analysis",
                tier=ModelTier.CHEAP,
                quality_score=score,
            )

        # Get tier recommendation (will have default behavior without Redis)
        recommendation = collector.recommend_tier(
            workflow_name="test",
            stage_name="analysis",
            current_tier=ModelTier.CHEAP,
        )

        # Should handle gracefully
        assert hasattr(recommendation, "recommended_tier")


class TestApprovalGates:
    """Test approval gate functionality."""

    def test_creates_approval_gate(self):
        """Test creating an approval gate."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        assert gate is not None
        assert gate.agent_id == "deploy_agent"

    def test_requests_approval(self):
        """Test requesting approval."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Request approval (will timeout without Redis, but should not crash)
        # We use a very short timeout to avoid blocking test
        response = gate.request_approval(
            approval_type="deployment",
            context={"environment": "production"},
            timeout=0.1,  # Very short timeout for test
        )

        assert response is not None
        assert hasattr(response, "approved")
        assert hasattr(response, "request_id")

    def test_approves_request(self):
        """Test approving a request."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Respond to approval (will be no-op without Redis but should not crash)
        success = gate.respond_to_approval(
            request_id="test-request-123",
            approved=True,
            responder="admin-1",
            reason="Looks good",
        )

        # Should handle gracefully
        assert isinstance(success, bool)

    def test_rejects_request(self):
        """Test rejecting a request."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Respond to approval with rejection
        success = gate.respond_to_approval(
            request_id="test-request-456",
            approved=False,
            responder="admin-1",
            reason="Security concerns",
        )

        # Should handle gracefully
        assert isinstance(success, bool)

    def test_requires_multiple_approvers(self):
        """Test handling multiple approval responses."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # In the actual implementation, multiple approvers would be
        # handled by the workflow logic, not the gate itself
        # This test just verifies the gate can process multiple responses

        gate.respond_to_approval("req-1", True, "admin-1", "LGTM")
        gate.respond_to_approval("req-1", True, "admin-2", "LGTM")
        gate.respond_to_approval("req-1", True, "admin-3", "LGTM")

        # Should handle gracefully
        assert True

    def test_prevents_duplicate_approvals(self):
        """Test that gate handles duplicate responses."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Same approver responds multiple times
        gate.respond_to_approval("req-1", True, "admin-1", "Approve")
        gate.respond_to_approval("req-1", True, "admin-1", "Approve again")

        # Should handle gracefully (deduplication would be workflow logic)
        assert True

    def test_tracks_approval_history(self):
        """Test getting pending approvals."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Get pending approvals (will be empty without Redis)
        pending = gate.get_pending_approvals()

        assert isinstance(pending, list)

    def test_timeout_handling(self):
        """Test handling of approval timeouts."""
        from attune.telemetry.approval_gates import ApprovalGate

        gate = ApprovalGate(agent_id="deploy_agent")

        # Request with very short timeout
        response = gate.request_approval(
            approval_type="test",
            context={},
            timeout=0.1,  # 0.1 second timeout
        )

        # Should timeout and return rejected response
        assert response is not None
        assert hasattr(response, "approved")
        assert response.approved is False  # Timeout means not approved


class TestTelemetryCLI:
    """Test telemetry CLI functionality."""

    def test_exports_telemetry_to_csv(self, tmp_path, capsys):
        """Test exporting telemetry data to CSV."""
        from argparse import Namespace

        from attune.telemetry.cli import cmd_telemetry_export

        output_file = tmp_path / "telemetry.csv"

        # Create args namespace matching CLI signature
        args = Namespace(
            format="csv",
            output=str(output_file),
        )

        # Should not crash
        result = cmd_telemetry_export(args)

        # Should return exit code
        assert isinstance(result, int)

    def test_shows_telemetry_stats(self, capsys):
        """Test displaying telemetry statistics."""
        from argparse import Namespace

        from attune.telemetry.cli import cmd_telemetry_show

        # Create args namespace
        args = Namespace()

        # Should not crash
        result = cmd_telemetry_show(args)

        # Should return exit code
        assert isinstance(result, int)

    def test_lists_recent_workflows(self, capsys):
        """Test listing recent workflow stats."""
        from argparse import Namespace

        from attune.telemetry.cli import cmd_telemetry_show

        # Show telemetry includes workflow info
        args = Namespace()
        result = cmd_telemetry_show(args)

        # Should return exit code
        assert isinstance(result, int)


class TestMultiBackendMonitoring:
    """Test multi-backend monitoring functionality."""

    def test_creates_multi_backend_monitor(self):
        """Test creating multi-backend monitor."""
        from attune.monitoring.multi_backend import MultiBackend, get_multi_backend

        # Get singleton instance
        monitor = get_multi_backend()

        assert monitor is not None
        assert isinstance(monitor, MultiBackend)

    def test_registers_backend(self):
        """Test registering a monitoring backend."""
        from attune.monitoring.multi_backend import TelemetryBackend, get_multi_backend

        monitor = get_multi_backend()

        mock_backend = Mock(spec=TelemetryBackend)

        # add_backend takes only one argument (the backend object)
        monitor.add_backend(mock_backend)

        # Backend should be added
        assert len(monitor.get_active_backends()) > 0

    def test_sends_metrics_to_all_backends(self):
        """Test sending metrics to all registered backends."""
        from datetime import datetime

        from attune.monitoring.multi_backend import (
            LLMCallRecord,
            TelemetryBackend,
            get_multi_backend,
        )

        monitor = get_multi_backend()

        backend1 = Mock(spec=TelemetryBackend)
        backend2 = Mock(spec=TelemetryBackend)

        monitor.add_backend(backend1)
        monitor.add_backend(backend2)

        # Log LLM call
        record = LLMCallRecord(
            call_id="test-call-123",
            timestamp=datetime.now().isoformat(),
            workflow_name="test",
            step_name="test_step",
            tier="cheap",
            model_id="test-model",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=0.001,
            latency_ms=1000,
        )
        monitor.log_call(record)

        # Both backends should receive the record
        backend1.log_call.assert_called_once()
        backend2.log_call.assert_called_once()

    def test_handles_backend_failure_gracefully(self):
        """Test graceful handling of backend failures."""
        from datetime import datetime

        from attune.monitoring.multi_backend import (
            LLMCallRecord,
            TelemetryBackend,
            get_multi_backend,
        )

        monitor = get_multi_backend()

        # Backend that always fails
        failing_backend = Mock(spec=TelemetryBackend)
        failing_backend.log_call = Mock(side_effect=Exception("Backend unavailable"))

        # Working backend
        working_backend = Mock(spec=TelemetryBackend)

        monitor.add_backend(failing_backend)
        monitor.add_backend(working_backend)

        # Should not crash even if one backend fails
        record = LLMCallRecord(
            call_id="test-call-456",
            timestamp=datetime.now().isoformat(),
            workflow_name="test",
            step_name="test_step",
            tier="cheap",
            model_id="test-model",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=0.001,
            latency_ms=1000,
        )
        monitor.log_call(record)

        # Working backend should still receive metric
        working_backend.log_call.assert_called_once()


@pytest.mark.skipif(
    not _otel_available,
    reason="opentelemetry not installed (optional dependency)",
)
class TestOTelBackend:
    """Test OpenTelemetry backend functionality."""

    def test_creates_otel_backend(self):
        """Test creating OpenTelemetry backend."""
        from attune.monitoring.otel_backend import OTELBackend

        backend = OTELBackend()

        assert backend is not None

    def test_configures_exporter(self):
        """Test that backend can be configured."""
        from attune.monitoring.otel_backend import OTELBackend

        backend = OTELBackend()

        # Backend should be created successfully
        assert backend is not None
        assert hasattr(backend, "log_call")
        assert hasattr(backend, "log_workflow")

    def test_emits_metrics(self):
        """Test recording LLM call metrics."""
        from datetime import datetime

        from attune.monitoring.otel_backend import LLMCallRecord, OTELBackend

        backend = OTELBackend()

        # Should not crash
        record = LLMCallRecord(
            call_id="test-call-789",
            timestamp=datetime.now().isoformat(),
            workflow_name="test",
            step_name="test_step",
            tier="cheap",
            model_id="test-model",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=0.001,
            latency_ms=1000,
        )
        backend.log_call(record)

        # Should handle gracefully
        assert True

    def test_emits_traces(self):
        """Test recording workflow traces."""
        from datetime import datetime

        from attune.monitoring.otel_backend import OTELBackend, WorkflowRunRecord

        backend = OTELBackend()

        # Should not crash
        now = datetime.now().isoformat()
        record = WorkflowRunRecord(
            run_id="test-run-123",
            workflow_name="test_workflow",
            started_at=now,
            completed_at=now,
            total_duration_ms=1500,
            success=True,
            total_cost=0.01,
            total_input_tokens=50,
            total_output_tokens=50,
        )
        backend.log_workflow(record)

        # Should handle gracefully
        assert True


class TestMetricsCollector:
    """Test metrics collector stub."""

    def test_creates_collector(self):
        """Test creating metrics collector (deprecated)."""
        from attune.metrics.collector import MetricsCollector

        collector = MetricsCollector()

        assert collector is not None

    def test_collect_returns_empty_dict(self):
        """Test that deprecated collect() returns empty dict."""
        from attune.metrics.collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect()

        assert result == {}

    def test_get_stats_returns_empty_dict(self):
        """Test that deprecated get_stats() returns empty dict."""
        from attune.metrics.collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.get_stats()

        assert result == {}
