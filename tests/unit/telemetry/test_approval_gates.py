"""Unit tests for Approval Gates (Pattern 5).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

from attune.telemetry.approval_gates import ApprovalGate, ApprovalRequest, ApprovalResponse
from tests.unit.telemetry.conftest import serve_mget_from_get


class TestApprovalRequest:
    """Test ApprovalRequest dataclass."""

    def test_approval_request_creation(self):
        """Test creating an ApprovalRequest."""
        request = ApprovalRequest(
            request_id="approval_abc123",
            approval_type="deploy_to_production",
            agent_id="workflow-001",
            context={"version": "2.0.0", "risk": "medium"},
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            timeout_seconds=300.0,
            status="pending",
        )

        assert request.request_id == "approval_abc123"
        assert request.approval_type == "deploy_to_production"
        assert request.agent_id == "workflow-001"
        assert request.context["version"] == "2.0.0"
        assert request.status == "pending"

    def test_to_dict(self):
        """Test converting ApprovalRequest to dict."""
        request = ApprovalRequest(
            request_id="approval_abc123",
            approval_type="delete_resource",
            agent_id="workflow-002",
            context={"resource_id": "res-123"},
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            timeout_seconds=180.0,
        )

        request_dict = request.to_dict()

        assert request_dict["request_id"] == "approval_abc123"
        assert request_dict["approval_type"] == "delete_resource"
        assert request_dict["timestamp"] == "2026-01-27T12:00:00"
        assert request_dict["timeout_seconds"] == 180.0

    def test_from_dict(self):
        """Test creating ApprovalRequest from dict."""
        data = {
            "request_id": "approval_xyz789",
            "approval_type": "refactor_code",
            "agent_id": "workflow-003",
            "context": {"files": ["a.py", "b.py"]},
            "timestamp": "2026-01-27T12:00:00",
            "timeout_seconds": 600.0,
            "status": "pending",
        }

        request = ApprovalRequest.from_dict(data)

        assert request.request_id == "approval_xyz789"
        assert request.approval_type == "refactor_code"
        assert request.context["files"] == ["a.py", "b.py"]


class TestApprovalResponse:
    """Test ApprovalResponse dataclass."""

    def test_approval_response_creation(self):
        """Test creating an ApprovalResponse."""
        response = ApprovalResponse(
            request_id="approval_abc123",
            approved=True,
            responder="user@example.com",
            reason="Looks good to deploy",
            timestamp=datetime(2026, 1, 27, 12, 5, 0),
        )

        assert response.request_id == "approval_abc123"
        assert response.approved is True
        assert response.responder == "user@example.com"
        assert response.reason == "Looks good to deploy"

    def test_to_dict(self):
        """Test converting ApprovalResponse to dict."""
        response = ApprovalResponse(
            request_id="approval_abc123",
            approved=False,
            responder="admin@example.com",
            reason="Too risky",
            timestamp=datetime(2026, 1, 27, 12, 5, 0),
        )

        response_dict = response.to_dict()

        assert response_dict["request_id"] == "approval_abc123"
        assert response_dict["approved"] is False
        assert response_dict["responder"] == "admin@example.com"
        assert response_dict["reason"] == "Too risky"

    def test_from_dict(self):
        """Test creating ApprovalResponse from dict."""
        data = {
            "request_id": "approval_xyz789",
            "approved": True,
            "responder": "user@example.com",
            "reason": "Approved",
            "timestamp": "2026-01-27T12:05:00",
        }

        response = ApprovalResponse.from_dict(data)

        assert response.request_id == "approval_xyz789"
        assert response.approved is True
        assert response.responder == "user@example.com"


class TestApprovalGate:
    """Test ApprovalGate class."""

    def test_init_without_memory(self):
        """Test ApprovalGate initialization without memory backend."""
        gate = ApprovalGate()

        assert gate.memory is None
        assert gate.agent_id is None

    def test_init_with_memory(self):
        """Test ApprovalGate initialization with memory backend."""
        mock_memory = Mock()
        gate = ApprovalGate(memory=mock_memory, agent_id="test-agent")

        assert gate.memory == mock_memory
        assert gate.agent_id == "test-agent"

    def test_request_approval_without_memory(self):
        """Test request_approval returns auto-rejected response when no memory."""
        gate = ApprovalGate()

        response = gate.request_approval(approval_type="test_approval", context={}, timeout=1.0)

        assert response.approved is False
        assert response.responder == "system"
        assert "not available" in response.reason

    def test_request_approval_stores_request(self):
        """Test that request_approval stores approval request in memory."""
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory._client = mock_client
        # Don't provide stash method, so it will use Redis directly
        del mock_memory.stash

        gate = ApprovalGate(memory=mock_memory, agent_id="test-agent")

        # Mock response after short timeout
        with patch.object(gate, "_check_for_response", return_value=None):
            with patch("time.sleep"):  # Speed up test
                response = gate.request_approval(
                    approval_type="deploy",
                    context={"version": "2.0.0"},
                    timeout=0.1,
                )

        # Should have stored the request
        assert mock_client.setex.called
        call_args = mock_client.setex.call_args[0]
        assert call_args[0].startswith("approval_request:")

        # Should timeout since no response
        assert response.approved is False
        assert response.responder == "system"
        assert "timeout" in response.reason.lower()

    def test_request_approval_receives_approved_response(self):
        """Test successful approval flow."""
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory, agent_id="test-agent")

        # Mock immediate approval response
        approved_response = ApprovalResponse(
            request_id="approval_test",
            approved=True,
            responder="user@example.com",
            reason="Approved",
        )

        with patch.object(gate, "_check_for_response", return_value=approved_response):
            response = gate.request_approval(
                approval_type="deploy",
                context={"version": "2.0.0"},
                timeout=5.0,
            )

        assert response.approved is True
        assert response.responder == "user@example.com"
        assert response.reason == "Approved"

    def test_request_approval_receives_rejected_response(self):
        """Test rejection flow."""
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory, agent_id="test-agent")

        # Mock immediate rejection response
        rejected_response = ApprovalResponse(
            request_id="approval_test",
            approved=False,
            responder="admin@example.com",
            reason="Too risky",
        )

        with patch.object(gate, "_check_for_response", return_value=rejected_response):
            response = gate.request_approval(
                approval_type="deploy",
                context={"version": "2.0.0"},
                timeout=5.0,
            )

        assert response.approved is False
        assert response.responder == "admin@example.com"
        assert response.reason == "Too risky"

    def test_respond_to_approval_success(self):
        """Test successful approval response."""
        mock_client = Mock()
        mock_client.get.return_value = b'{"request_id": "approval_abc123", "approval_type": "deploy", "agent_id": "test", "context": {}, "timestamp": "2026-01-27T12:00:00", "timeout_seconds": 300, "status": "pending"}'

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        success = gate.respond_to_approval(
            request_id="approval_abc123",
            approved=True,
            responder="user@example.com",
            reason="Looks good",
        )

        assert success is True
        # Should have stored response via pipeline
        assert mock_client.pipeline.called
        pipe = mock_client.pipeline.return_value
        assert pipe.setex.called
        assert pipe.execute.called

    def test_respond_to_approval_without_memory(self):
        """Test respond_to_approval returns False when no memory."""
        gate = ApprovalGate()

        success = gate.respond_to_approval(
            request_id="approval_abc123",
            approved=True,
            responder="user@example.com",
        )

        assert success is False

    def test_get_pending_approvals_empty(self):
        """Test get_pending_approvals returns empty list when no requests."""
        mock_client = Mock()
        mock_client.scan_iter.return_value = []

        mock_memory = Mock()
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        pending = gate.get_pending_approvals()

        assert pending == []

    def test_get_pending_approvals_with_requests(self):
        """Test get_pending_approvals returns pending requests."""
        mock_client = Mock()

        # Return list of keys
        keys_list = [b"approval_request:approval_abc123", b"approval_request:approval_xyz789"]
        mock_client.scan_iter.return_value = keys_list

        # Mock request data
        request1_data = {
            "request_id": "approval_abc123",
            "approval_type": "deploy",
            "agent_id": "workflow-1",
            "context": {"version": "2.0.0"},
            "timestamp": "2026-01-27T12:00:00",
            "timeout_seconds": 300,
            "status": "pending",
        }

        request2_data = {
            "request_id": "approval_xyz789",
            "approval_type": "delete",
            "agent_id": "workflow-2",
            "context": {"resource": "res-123"},
            "timestamp": "2026-01-27T12:05:00",
            "timeout_seconds": 180,
            "status": "pending",
        }

        import json

        def mock_get(key):
            # Decode bytes keys
            if isinstance(key, bytes):
                key = key.decode()

            if "approval_abc123" in key:
                return json.dumps(request1_data).encode()
            if "approval_xyz789" in key:
                return json.dumps(request2_data).encode()
            return None

        mock_client.get.side_effect = mock_get
        serve_mget_from_get(mock_client)

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        pending = gate.get_pending_approvals()

        assert len(pending) == 2
        assert pending[0].request_id == "approval_abc123"
        assert pending[1].request_id == "approval_xyz789"

    def test_get_pending_approvals_filters_by_type(self):
        """Test get_pending_approvals filters by approval_type."""
        mock_client = Mock()

        keys_list = [b"approval_request:approval_abc123", b"approval_request:approval_xyz789"]
        mock_client.scan_iter.return_value = keys_list

        # Mock request data
        request1_data = {
            "request_id": "approval_abc123",
            "approval_type": "deploy",
            "agent_id": "workflow-1",
            "context": {},
            "timestamp": "2026-01-27T12:00:00",
            "timeout_seconds": 300,
            "status": "pending",
        }

        request2_data = {
            "request_id": "approval_xyz789",
            "approval_type": "delete",
            "agent_id": "workflow-2",
            "context": {},
            "timestamp": "2026-01-27T12:05:00",
            "timeout_seconds": 180,
            "status": "pending",
        }

        import json

        def mock_get(key):
            if isinstance(key, bytes):
                key = key.decode()

            if "approval_abc123" in key:
                return json.dumps(request1_data).encode()
            if "approval_xyz789" in key:
                return json.dumps(request2_data).encode()
            return None

        mock_client.get.side_effect = mock_get
        serve_mget_from_get(mock_client)

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        # Filter for deploy type only
        pending = gate.get_pending_approvals(approval_type="deploy")

        assert len(pending) == 1
        assert pending[0].approval_type == "deploy"

    def test_get_pending_approvals_excludes_non_pending(self):
        """Test get_pending_approvals excludes approved/rejected/timeout requests."""
        mock_client = Mock()
        mock_client.scan_iter.return_value = [b"approval_request:approval_abc123"]

        # Mock approved request (should be excluded)
        request_data = {
            "request_id": "approval_abc123",
            "approval_type": "deploy",
            "agent_id": "workflow-1",
            "context": {},
            "timestamp": "2026-01-27T12:00:00",
            "timeout_seconds": 300,
            "status": "approved",  # Not pending
        }

        import json

        mock_client.get.return_value = json.dumps(request_data).encode()
        serve_mget_from_get(mock_client)

        mock_memory = Mock()
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        pending = gate.get_pending_approvals()

        assert pending == []

    def test_clear_expired_requests(self):
        """Test clearing expired approval requests."""
        mock_client = Mock()

        keys_list = [b"approval_request:approval_abc123"]
        mock_client.scan_iter.return_value = keys_list

        # Mock expired request
        request_data = {
            "request_id": "approval_abc123",
            "approval_type": "deploy",
            "agent_id": "workflow-1",
            "context": {},
            "timestamp": "2026-01-27T11:00:00",  # 1 hour ago
            "timeout_seconds": 300,  # 5 minutes timeout
            "status": "pending",
        }

        import json

        mock_client.get.return_value = json.dumps(request_data).encode()
        serve_mget_from_get(mock_client)

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        cleared = gate.clear_expired_requests()

        assert cleared == 1
        # Should have updated status to timeout
        assert mock_client.setex.called


class TestApprovalGateIntegration:
    """Integration tests for approval gate workflow."""

    def test_full_approval_flow(self):
        """Test complete approval flow: request → respond → receive."""
        mock_client = Mock()

        # Track stored data
        stored_data = {}

        def mock_setex(key, ttl, value):
            stored_data[key] = value
            return True

        def mock_get(key):
            return stored_data.get(key)

        mock_client.setex.side_effect = mock_setex
        mock_client.get.side_effect = mock_get
        serve_mget_from_get(mock_client)

        # Pipeline mock: respond_to_approval() uses pipeline for batching
        mock_pipe = Mock()
        mock_pipe.setex.side_effect = mock_setex
        mock_pipe.execute.return_value = [True]
        mock_client.pipeline.return_value = mock_pipe

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        # Workflow: Request approval
        workflow_gate = ApprovalGate(memory=mock_memory, agent_id="workflow-001")

        # Simulate: Start approval request in background
        import threading

        def respond_after_delay():
            time.sleep(0.5)
            # UI: Respond to approval
            # Find the request_id from stored keys
            request_keys = [k for k in stored_data if k.startswith("approval_request:")]
            if request_keys:
                request_id = request_keys[0].replace("approval_request:", "")
                ui_gate = ApprovalGate(memory=mock_memory)
                ui_gate.respond_to_approval(
                    request_id=request_id,
                    approved=True,
                    responder="user@example.com",
                    reason="Approved",
                )

        response_thread = threading.Thread(target=respond_after_delay)
        response_thread.start()

        # Request approval (blocks until response)
        response = workflow_gate.request_approval(
            approval_type="deploy",
            context={"version": "2.0.0"},
            timeout=5.0,
        )

        response_thread.join()

        # Verify approval was received
        assert response.approved is True
        assert response.responder == "user@example.com"


# =============================================================================
# Branch-coverage additions — targets previously-uncovered lines
# =============================================================================


class TestApprovalRequestFromDictBranches:
    """Cover from_dict timestamp branches (lines 91-94)."""

    def test_from_dict_timestamp_not_datetime_not_str(self):
        data = {
            "request_id": "r1",
            "approval_type": "deploy",
            "agent_id": "agent1",
            "timestamp": None,  # Neither str nor datetime
        }
        req = ApprovalRequest.from_dict(data)
        assert req.timestamp.tzinfo is not None

    def test_from_dict_timestamp_naive_datetime_gets_utc(self):
        naive = datetime(2025, 1, 1, 12, 0, 0)  # No tzinfo
        data = {
            "request_id": "r2",
            "approval_type": "delete",
            "agent_id": "agent2",
            "timestamp": naive,
        }
        req = ApprovalRequest.from_dict(data)
        assert req.timestamp.tzinfo is not None


class TestApprovalResponseFromDictBranches:
    """Cover from_dict timestamp branches in ApprovalResponse (lines 142-145)."""

    def test_from_dict_timestamp_none_gets_utc(self):
        data = {
            "request_id": "r3",
            "approved": True,
            "responder": "user@example.com",
            "timestamp": None,
        }
        resp = ApprovalResponse.from_dict(data)
        assert resp.timestamp.tzinfo is not None

    def test_from_dict_timestamp_naive_datetime_gets_utc(self):
        naive = datetime(2025, 6, 1, 8, 0, 0)
        data = {
            "request_id": "r4",
            "approved": False,
            "responder": "bot",
            "timestamp": naive,
        }
        resp = ApprovalResponse.from_dict(data)
        assert resp.timestamp.tzinfo is not None


class TestApprovalGateNoBranchCoverage:
    """Cover branches where memory/agent_id missing or no Redis client."""

    def test_request_approval_no_memory_returns_rejected(self):
        gate = ApprovalGate(memory=None, agent_id=None)
        gate.memory = None
        response = gate.request_approval("deploy", context={}, timeout=0.1)
        assert response.approved is False

    def test_respond_to_approval_no_memory_returns_false(self):
        gate = ApprovalGate(memory=None, agent_id="wf")
        gate.memory = None
        result = gate.respond_to_approval("req1", approved=True, responder="user")
        assert result is False

    def test_respond_to_approval_no_redis_client_returns_false(self):
        mock_memory = MagicMock()
        mock_memory._client = None  # No Redis backend
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        result = gate.respond_to_approval("req1", approved=True, responder="user")
        assert result is False

    def test_check_for_response_no_memory_returns_none(self):
        gate = ApprovalGate(memory=None, agent_id="wf")
        gate.memory = None
        result = gate._check_for_response("req1")
        assert result is None

    def test_check_for_response_retrieve_method(self):
        mock_memory = MagicMock(spec=["retrieve"])
        mock_memory.retrieve.return_value = None
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        result = gate._check_for_response("req1")
        assert result is None

    def test_check_for_response_redis_client_no_data(self):
        mock_memory = MagicMock(spec=["_client"])
        mock_memory._client.get.return_value = None
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        result = gate._check_for_response("req1")
        assert result is None

    def test_check_for_response_redis_bytes_decoded(self):
        import json

        response_data = {
            "request_id": "r1",
            "approved": True,
            "responder": "user",
            "reason": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mock_memory = MagicMock(spec=["_client"])
        mock_memory._client.get.return_value = json.dumps(response_data).encode("utf-8")
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        result = gate._check_for_response("r1")
        assert result is not None
        assert result.approved is True

    def test_check_for_response_exception_returns_none(self):
        mock_memory = MagicMock(spec=["retrieve"])
        mock_memory.retrieve.side_effect = RuntimeError("redis error")
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        result = gate._check_for_response("req1")
        assert result is None

    def test_request_approval_no_redis_client_logs_warning(self, caplog):
        import logging

        mock_memory = MagicMock()
        mock_memory._client = None
        # _check_for_response uses retrieve(); make it return None so no response found
        mock_memory.retrieve.return_value = None
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        with caplog.at_level(logging.WARNING):
            # times out immediately since poll loop never gets response
            response = gate.request_approval("deploy", timeout=0.01)
        assert response.approved is False


class TestApprovalGateInitMemoryResolution:
    """Cover __init__ memory resolution via UsageTracker (lines 190-194)."""

    def test_init_adopts_usage_tracker_memory(self):
        """When no memory is given, the gate adopts UsageTracker's backend."""
        sentinel = object()
        fake_tracker = Mock()
        fake_tracker._memory = sentinel

        with patch("attune.telemetry.UsageTracker") as mock_tracker_cls:
            mock_tracker_cls.get_instance.return_value = fake_tracker
            gate = ApprovalGate()

        assert gate.memory is sentinel

    def test_init_tracker_without_memory_attr_leaves_memory_none(self):
        """A tracker without a _memory attribute leaves the gate memoryless."""
        fake_tracker = Mock(spec=[])  # no _memory attribute

        with patch("attune.telemetry.UsageTracker") as mock_tracker_cls:
            mock_tracker_cls.get_instance.return_value = fake_tracker
            gate = ApprovalGate()

        assert gate.memory is None

    def test_init_tracker_lookup_failure_degrades_to_no_memory(self):
        """AttributeError from the tracker lookup degrades to no memory backend."""
        with patch("attune.telemetry.UsageTracker") as mock_tracker_cls:
            mock_tracker_cls.get_instance.side_effect = AttributeError("no instance")
            gate = ApprovalGate()

        assert gate.memory is None


class TestRequestApprovalErrorBranches:
    """Cover request_approval storage/signal/timeout error branches."""

    def test_storage_error_returns_rejected_with_reason(self):
        """A Redis write failure auto-rejects with a Storage error reason (269-271)."""
        mock_client = Mock()
        mock_client.setex.side_effect = RuntimeError("redis down")
        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        response = gate.request_approval("deploy", context={}, timeout=0.1)

        assert response.approved is False
        assert response.responder == "system"
        assert "Storage error" in response.reason
        assert response.request_id.startswith("approval_")

    def test_signal_failure_does_not_break_approval_flow(self):
        """A CoordinationSignals failure is non-fatal — approval still returns (290-291)."""
        mock_client = Mock()
        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory, agent_id="wf")
        approved = ApprovalResponse(
            request_id="r1",
            approved=True,
            responder="user@example.com",
        )

        with patch(
            "attune.telemetry.CoordinationSignals",
            side_effect=RuntimeError("signals unavailable"),
        ):
            with patch.object(gate, "_check_for_response", return_value=approved):
                response = gate.request_approval("deploy", timeout=5.0)

        assert response.approved is True
        assert response.responder == "user@example.com"

    def test_timeout_status_update_failure_still_returns_timeout(self):
        """A Redis failure while marking timeout is swallowed (322-323)."""
        mock_client = Mock()
        # First setex stores the request; second (timeout status update) fails.
        mock_client.setex.side_effect = [True, RuntimeError("redis gone")]
        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory, agent_id="wf")

        with patch("attune.telemetry.CoordinationSignals"):
            with patch.object(gate, "_check_for_response", return_value=None):
                with patch("time.sleep"):
                    response = gate.request_approval("deploy", timeout=0.05)

        assert response.approved is False
        assert "timeout" in response.reason.lower()
        assert mock_client.setex.call_count == 2


class TestCheckForResponseFallback:
    """Cover the no-retrieve/no-client fallback in _check_for_response (355)."""

    def test_memory_without_retrieve_or_client_returns_none(self):
        mock_memory = Mock(spec=[])  # neither retrieve nor _client
        gate = ApprovalGate(memory=mock_memory, agent_id="wf")

        assert gate._check_for_response("r1") is None


class TestRespondToApprovalBranches:
    """Cover respond_to_approval retrieve-path, pipeline failure, signal failure."""

    @staticmethod
    def _request_data(status="pending"):
        return {
            "request_id": "r1",
            "approval_type": "deploy",
            "agent_id": "wf",
            "context": {},
            "timestamp": "2026-01-27T12:00:00",
            "timeout_seconds": 300,
            "status": status,
        }

    def test_reads_request_via_retrieve_and_updates_status(self):
        """Memory exposing retrieve() is used to read the request (418)."""
        import json

        mock_client = Mock()
        mock_pipe = Mock()
        mock_client.pipeline.return_value = mock_pipe

        mock_memory = Mock(spec=["_client", "retrieve"])
        mock_memory._client = mock_client
        mock_memory.retrieve.return_value = self._request_data()

        gate = ApprovalGate(memory=mock_memory)
        ok = gate.respond_to_approval(
            request_id="r1",
            approved=False,
            responder="admin@example.com",
            reason="Too risky",
        )

        assert ok is True
        mock_memory.retrieve.assert_called_once_with("approval_request:r1", credentials=None)
        # Two writes pipelined: the response, then the status-updated request.
        assert mock_pipe.setex.call_count == 2
        updated_request = json.loads(mock_pipe.setex.call_args_list[1][0][2])
        assert updated_request["status"] == "rejected"

    def test_pipeline_failure_returns_false(self):
        """A pipeline execution error returns False (436-438)."""
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_pipe = Mock()
        mock_pipe.execute.side_effect = RuntimeError("pipeline failed")
        mock_client.pipeline.return_value = mock_pipe

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)
        ok = gate.respond_to_approval(
            request_id="r1",
            approved=True,
            responder="user@example.com",
        )

        assert ok is False

    def test_signal_failure_does_not_fail_response(self):
        """A CoordinationSignals failure is non-fatal — response still True (452-453)."""
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_pipe = Mock()
        mock_client.pipeline.return_value = mock_pipe

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)
        with patch(
            "attune.telemetry.CoordinationSignals",
            side_effect=RuntimeError("signals unavailable"),
        ):
            ok = gate.respond_to_approval(
                request_id="r1",
                approved=True,
                responder="user@example.com",
            )

        assert ok is True


class TestGetPendingApprovalsBranches:
    """Cover get_pending_approvals degradation branches."""

    def test_no_memory_returns_empty_list(self):
        """No memory backend degrades to an empty list (480)."""
        gate = ApprovalGate(memory=None)
        gate.memory = None

        assert gate.get_pending_approvals() == []

    def test_memory_without_client_returns_empty_list(self):
        mock_memory = Mock(spec=[])  # no _client
        gate = ApprovalGate(memory=mock_memory)

        assert gate.get_pending_approvals() == []

    def test_key_with_no_data_is_skipped(self):
        """A scanned key whose value expired is skipped, not an error (500, 503)."""
        mock_client = Mock()
        mock_client.scan_iter.return_value = [b"approval_request:r_gone"]
        mock_client.get.return_value = None
        serve_mget_from_get(mock_client)

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        assert gate.get_pending_approvals() == []

    def test_scan_error_returns_empty_list(self):
        """A Redis scan failure degrades to an empty list (521-523)."""
        mock_client = Mock()
        mock_client.scan_iter.side_effect = RuntimeError("scan failed")

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        assert gate.get_pending_approvals() == []


class TestClearExpiredRequestsBranches:
    """Cover clear_expired_requests degradation branches."""

    def test_no_memory_returns_zero(self):
        """No memory backend degrades to zero cleared (533)."""
        gate = ApprovalGate(memory=None)
        gate.memory = None

        assert gate.clear_expired_requests() == 0

    def test_memory_without_client_returns_zero(self):
        mock_memory = Mock(spec=[])  # no _client
        gate = ApprovalGate(memory=mock_memory)

        assert gate.clear_expired_requests() == 0

    def test_key_with_no_data_is_skipped(self):
        """A scanned key whose value expired is skipped, not counted (553, 556)."""
        mock_client = Mock()
        mock_client.scan_iter.return_value = [b"approval_request:r_gone"]
        mock_client.get.return_value = None
        serve_mget_from_get(mock_client)

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        assert gate.clear_expired_requests() == 0
        assert not mock_client.setex.called

    def test_scan_error_returns_zero(self):
        """A Redis scan failure degrades to zero cleared (574-576)."""
        mock_client = Mock()
        mock_client.scan_iter.side_effect = RuntimeError("scan failed")

        mock_memory = Mock(spec=["_client"])
        mock_memory._client = mock_client

        gate = ApprovalGate(memory=mock_memory)

        assert gate.clear_expired_requests() == 0
