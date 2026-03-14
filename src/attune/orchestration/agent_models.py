"""Agent result and quality gate models for orchestration.

These define the interface contract between agents and the
DynamicTeam executor.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SDKExecutionMode(Enum):
    """How the agent should run."""

    TOOLS_ONLY = "tools_only"
    FULL_SDK = "full_sdk"


@dataclass
class SDKAgentResult:
    """Result from a single agent execution.

    Args:
        agent_id: Unique identifier for the agent.
        role: Human-readable role name.
        success: Whether the agent completed successfully.
        tier_used: Model tier used (cheap, capable, premium).
        mode: Execution mode.
        findings: Structured findings dict.
        score: Numeric quality score (0-100).
        confidence: Confidence level (0-1).
        cost: LLM API cost in USD.
        execution_time_ms: Wall-clock time in milliseconds.
        escalated: Whether tier escalation occurred.
        sdk_used: Whether the Agent SDK was used.
        error: Error message if failed.

    """

    agent_id: str
    role: str
    success: bool = True
    tier_used: str = "cheap"
    mode: SDKExecutionMode = SDKExecutionMode.TOOLS_ONLY
    findings: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    cost: float = 0.0
    execution_time_ms: float = 0.0
    escalated: bool = False
    sdk_used: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "success": self.success,
            "tier_used": self.tier_used,
            "mode": self.mode.value,
            "findings": self.findings,
            "score": self.score,
            "confidence": self.confidence,
            "cost": self.cost,
            "execution_time_ms": self.execution_time_ms,
            "escalated": self.escalated,
            "sdk_used": self.sdk_used,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SDKAgentResult:
        """Deserialize from a dict."""
        mode_val = data.get("mode", "tools_only")
        if isinstance(mode_val, str):
            mode_val = SDKExecutionMode(mode_val)
        return cls(
            agent_id=data.get("agent_id", ""),
            role=data.get("role", ""),
            success=data.get("success", True),
            tier_used=data.get("tier_used", "cheap"),
            mode=mode_val,
            findings=data.get("findings", {}),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            cost=data.get("cost", 0.0),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            escalated=data.get("escalated", False),
            sdk_used=data.get("sdk_used", False),
            error=data.get("error"),
        )


@dataclass
class QualityGate:
    """A named threshold that an agent result must satisfy.

    Args:
        name: Gate name (e.g., "min_security_score").
        agent_role: Role name of agent whose result is checked.
        metric: Key in SDKAgentResult.findings to evaluate.
        threshold: Minimum acceptable value.
        required: If True, gate failure fails entire team.

    """

    name: str
    agent_role: str
    metric: str
    threshold: float
    required: bool = True


@runtime_checkable
class AgentLike(Protocol):
    """Protocol for objects that can participate in DynamicTeam execution."""

    agent_id: str
    role: str

    def process(self, input_data: dict[str, Any]) -> SDKAgentResult:
        """Execute the agent and return a result."""
        ...


class StubAgent:
    """Lightweight agent stub for DynamicTeam composition.

    Replaces the deleted ``SDKAgent`` scaffolding. Stores
    configuration but raises ``NotImplementedError`` on
    ``process()`` — the orchestration layer is not yet
    wired to a real execution backend.

    Args:
        agent_id: Unique identifier.
        role: Human-readable role name.
        system_prompt: Agent instructions.
        mode: Execution mode.

    """

    def __init__(
        self,
        agent_id: str | None = None,
        role: str = "Agent",
        system_prompt: str = "",
        mode: SDKExecutionMode = SDKExecutionMode.TOOLS_ONLY,
        **kwargs: Any,
    ) -> None:
        """Initialize StubAgent."""
        from uuid import uuid4

        self.agent_id = agent_id or f"stub-{uuid4().hex[:8]}"
        self.role = role
        self.system_prompt = system_prompt
        self.mode = mode
        # Store extra kwargs (e.g. state_store, redis_client)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def process(self, input_data: dict[str, Any]) -> SDKAgentResult:
        """Return a stub result for orchestration testing.

        Returns a minimal successful result. Wire a real agent
        backend for production use.

        """
        return SDKAgentResult(
            agent_id=self.agent_id,
            role=self.role,
            success=True,
            tier_used="cheap",
            mode=self.mode,
        )
