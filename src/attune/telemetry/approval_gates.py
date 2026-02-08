"""Human Approval Gates for Workflow Control.

Pattern 5 from Agent Coordination Architecture - Pause workflow execution
for human approval on critical decisions.

Usage:
    # In workflow: Request approval
    gate = ApprovalGate(agent_id="code-review-workflow")
    approval = gate.request_approval(
        approval_type="deploy_to_production",
        context={
            "deployment": "v2.0.0",
            "changes": ["feature-x", "bugfix-y"],
            "risk_level": "medium"
        },
        timeout=300.0  # 5 minutes
    )

    if approval.approved:
        deploy_to_production()
    else:
        logger.info(f"Deployment rejected: {approval.reason}")

    # From UI: Respond to approval request
    gate = ApprovalGate()
    pending = gate.get_pending_approvals()
    for request in pending:
        # Display to user, get decision
        gate.respond_to_approval(
            request_id=request.request_id,
            approved=True,
            responder="user@example.com",
            reason="Looks good to deploy"
        )

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Approval request with context for human decision.

    Represents a pending approval request from a workflow.
    """

    request_id: str
    approval_type: str  # "deploy", "delete", "refactor", etc.
    agent_id: str  # Requesting agent/workflow
    context: dict[str, Any]  # Decision context
    timestamp: datetime
    timeout_seconds: float
    status: str = "pending"  # "pending", "approved", "rejected", "timeout"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "approval_type": self.approval_type,
            "agent_id": self.agent_id,
            "context": self.context,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "timeout_seconds": self.timeout_seconds,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()

        return cls(
            request_id=data["request_id"],
            approval_type=data["approval_type"],
            agent_id=data["agent_id"],
            context=data.get("context", {}),
            timestamp=timestamp,
            timeout_seconds=data.get("timeout_seconds", 300.0),
            status=data.get("status", "pending"),
        )


@dataclass
class ApprovalResponse:
    """Response to an approval request.

    Represents a human's decision on an approval request.
    """

    request_id: str
    approved: bool
    responder: str  # User who approved/rejected
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "approved": self.approved,
            "responder": self.responder,
            "reason": self.reason,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalResponse:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()

        return cls(
            request_id=data["request_id"],
            approved=data.get("approved", False),
            responder=data.get("responder", "unknown"),
            reason=data.get("reason", ""),
            timestamp=timestamp,
        )


class ApprovalGate:
    """Human approval gates for workflow control.

    Workflows can pause execution and wait for human approval before
    proceeding with critical actions.

    Uses coordination signals under the hood:
    - "approval_request" signal: Workflow → Human
    - "approval_response" signal: Human → Workflow

    Attributes:
        DEFAULT_TIMEOUT: Default approval timeout (300s = 5 minutes)
        POLL_INTERVAL: Poll interval when waiting for approval (1s)
    """

    DEFAULT_TIMEOUT = 300.0  # 5 minutes default timeout
    POLL_INTERVAL = 1.0  # Check for response every 1 second

    def __init__(self, memory=None, agent_id: str | None = None):
        """Initialize approval gate.

        Args:
            memory: Memory instance for storing approval requests/responses
            agent_id: This agent's ID (for workflow requesting approval)
        """
        self.memory = memory
        self.agent_id = agent_id

        if self.memory is None:
            try:
                from attune.telemetry import UsageTracker

                tracker = UsageTracker.get_instance()
                if hasattr(tracker, "_memory"):
                    self.memory = tracker._memory
            except (ImportError, AttributeError):
                pass

        if self.memory is None:
            logger.warning("No memory backend available for approval gates")

    def request_approval(
        self,
        approval_type: str,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ApprovalResponse:
        """Request human approval and wait for response.

        This is a blocking operation that waits for human approval with timeout.

        Args:
            approval_type: Type of approval needed (e.g., "deploy", "delete")
            context: Context information for decision making
            timeout: Maximum wait time in seconds (default: DEFAULT_TIMEOUT)

        Returns:
            ApprovalResponse with decision (approved or rejected)

        Raises:
            ValueError: If approval times out

        Example:
            >>> gate = ApprovalGate(agent_id="my-workflow")
            >>> approval = gate.request_approval(
            ...     approval_type="deploy_to_production",
            ...     context={"version": "2.0.0", "risk": "medium"},
            ...     timeout=300.0
            ... )
            >>> if approval.approved:
            ...     deploy()
        """
        if not self.memory or not self.agent_id:
            logger.warning("Cannot request approval: no memory backend or agent_id")
            # Return auto-rejected response
            return ApprovalResponse(
                request_id="",
                approved=False,
                responder="system",
                reason="Approval gates not available (no memory backend)",
            )

        timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        request_id = f"approval_{uuid4().hex[:8]}"

        # Create approval request
        request = ApprovalRequest(
            request_id=request_id,
            approval_type=approval_type,
            agent_id=self.agent_id,
            context=context or {},
            timestamp=datetime.utcnow(),
            timeout_seconds=timeout,
            status="pending",
        )

        # Store approval request (for UI to retrieve)
        request_key = f"approval_request:{request_id}"
        try:
            # Use direct Redis access for custom TTL
            if hasattr(self.memory, "_client") and self.memory._client:
                import json

                self.memory._client.setex(
                    request_key, int(timeout) + 60, json.dumps(request.to_dict())
                )
            else:
                logger.warning("Cannot store approval request: no Redis backend available")
        except Exception as e:
            logger.error(f"Failed to store approval request: {e}")
            return ApprovalResponse(
                request_id=request_id,
                approved=False,
                responder="system",
                reason=f"Storage error: {e}",
            )

        # Send approval_request signal (for notifications)
        try:
            from attune.telemetry import CoordinationSignals

            signals = CoordinationSignals(memory=self.memory, agent_id=self.agent_id)
            signals.signal(
                signal_type="approval_request",
                source_agent=self.agent_id,
                target_agent="*",  # Broadcast to UI/monitoring systems
                payload=request.to_dict(),
                ttl_seconds=int(timeout) + 60,
            )
        except Exception as e:
            logger.warning(f"Failed to send approval_request signal: {e}")

        # Wait for approval response (blocking with timeout)
        logger.info(
            f"Waiting for approval: {approval_type} (request_id={request_id}, timeout={timeout}s)"
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for response
            response = self._check_for_response(request_id)
            if response:
                logger.info(
                    f"Approval received: {approval_type} → {'APPROVED' if response.approved else 'REJECTED'}"
                )
                return response

            # Sleep before next check
            time.sleep(self.POLL_INTERVAL)

        # Timeout - no response received
        logger.warning(f"Approval timeout: {approval_type} (request_id={request_id})")

        # Update request status to timeout
        request.status = "timeout"
        try:
            # Use direct Redis access
            if hasattr(self.memory, "_client") and self.memory._client:
                import json

                self.memory._client.setex(request_key, 60, json.dumps(request.to_dict()))
        except Exception:
            pass

        return ApprovalResponse(
            request_id=request_id,
            approved=False,
            responder="system",
            reason=f"Approval timeout after {timeout}s",
        )

    def _check_for_response(self, request_id: str) -> ApprovalResponse | None:
        """Check if approval response has been received."""
        if not self.memory:
            return None

        response_key = f"approval_response:{request_id}"

        try:
            # Try retrieve method first (UnifiedMemory)
            if hasattr(self.memory, "retrieve"):
                data = self.memory.retrieve(response_key, credentials=None)
            # Try direct Redis access
            elif hasattr(self.memory, "_client"):
                import json

                raw_data = self.memory._client.get(response_key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    data = json.loads(raw_data)
                else:
                    data = None
            else:
                data = None

            if data:
                return ApprovalResponse.from_dict(data)
            return None
        except Exception as e:
            logger.debug(f"Failed to check for approval response: {e}")
            return None

    def respond_to_approval(
        self, request_id: str, approved: bool, responder: str, reason: str = ""
    ) -> bool:
        """Respond to an approval request (called from UI/human).

        Args:
            request_id: ID of approval request to respond to
            approved: Whether to approve or reject
            responder: User/system responding (e.g., email, username)
            reason: Optional reason for decision

        Returns:
            True if response was stored successfully, False otherwise

        Example:
            >>> gate = ApprovalGate()
            >>> success = gate.respond_to_approval(
            ...     request_id="approval_abc123",
            ...     approved=True,
            ...     responder="user@example.com",
            ...     reason="Looks good to deploy"
            ... )
        """
        if not self.memory:
            logger.warning("Cannot respond to approval: no memory backend")
            return False

        response = ApprovalResponse(
            request_id=request_id,
            approved=approved,
            responder=responder,
            reason=reason,
            timestamp=datetime.utcnow(),
        )

        # Store approval response and update request status
        response_key = f"approval_response:{request_id}"
        request_key = f"approval_request:{request_id}"

        if not hasattr(self.memory, "_client") or not self.memory._client:
            logger.warning("Cannot store approval response: no Redis backend available")
            return False

        import json

        try:
            # Read current request data first
            request_data = None
            if hasattr(self.memory, "retrieve"):
                request_data = self.memory.retrieve(request_key, credentials=None)
            else:
                raw_data = self.memory._client.get(request_key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    request_data = json.loads(raw_data)

            # Pipeline both writes to reduce round trips
            pipe = self.memory._client.pipeline()
            pipe.setex(response_key, 300, json.dumps(response.to_dict()))

            if request_data:
                request = ApprovalRequest.from_dict(request_data)
                request.status = "approved" if approved else "rejected"
                pipe.setex(request_key, 300, json.dumps(request.to_dict()))

            pipe.execute()
        except Exception as e:
            logger.error(f"Failed to store approval response: {e}")
            return False

        # Send approval_response signal (for notifications)
        try:
            from attune.telemetry import CoordinationSignals

            signals = CoordinationSignals(memory=self.memory, agent_id=responder)
            signals.signal(
                signal_type="approval_response",
                source_agent=responder,
                target_agent="*",  # Broadcast
                payload=response.to_dict(),
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"Failed to send approval_response signal: {e}")

        logger.info(
            "Approval response recorded: %s → %s by %s",
            request_id,
            "APPROVED" if approved else "REJECTED",
            responder,
        )
        return True

    def get_pending_approvals(self, approval_type: str | None = None) -> list[ApprovalRequest]:
        """Get all pending approval requests (called from UI).

        Args:
            approval_type: Optional filter by approval type

        Returns:
            List of pending approval requests

        Example:
            >>> gate = ApprovalGate()
            >>> pending = gate.get_pending_approvals()
            >>> for request in pending:
            ...     print(f"{request.approval_type}: {request.context}")
        """
        if not self.memory or not hasattr(self.memory, "_client"):
            return []

        try:
            # Scan for approval_request:* keys
            keys = list(self.memory._client.scan_iter(match="approval_request:*", count=100))

            requests = []
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                # Retrieve request - use direct Redis access (approval keys are stored without prefix)
                import json

                raw_data = self.memory._client.get(key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    data = json.loads(raw_data)
                else:
                    data = None

                if not data:
                    continue

                request = ApprovalRequest.from_dict(data)

                # Filter by status (only pending)
                if request.status != "pending":
                    continue

                # Filter by type if specified
                if approval_type and request.approval_type != approval_type:
                    continue

                requests.append(request)

            # Sort by timestamp (oldest first)
            requests.sort(key=lambda r: r.timestamp)

            return requests
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    def clear_expired_requests(self) -> int:
        """Clear approval requests that have timed out.

        Returns:
            Number of requests cleared
        """
        if not self.memory or not hasattr(self.memory, "_client"):
            return 0

        try:
            keys = list(self.memory._client.scan_iter(match="approval_request:*", count=100))
            now = datetime.utcnow()
            cleared = 0

            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                # Retrieve request - use direct Redis access (approval keys are stored without prefix)
                import json

                raw_data = self.memory._client.get(key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    data = json.loads(raw_data)
                else:
                    data = None

                if not data:
                    continue

                request = ApprovalRequest.from_dict(data)

                # Check if expired
                elapsed = (now - request.timestamp).total_seconds()
                if elapsed > request.timeout_seconds and request.status == "pending":
                    # Update to timeout status
                    request.status = "timeout"
                    # Use direct Redis access
                    if hasattr(self.memory, "_client") and self.memory._client:
                        import json

                        self.memory._client.setex(key, 60, json.dumps(request.to_dict()))

                    cleared += 1

            return cleared
        except Exception as e:
            logger.error(f"Failed to clear expired requests: {e}")
            return 0
