"""Data models for Anthropic Agent SDK integration.

Defines result types, execution modes, and SDK availability detection.
The SDK is an optional dependency; all code gracefully degrades when
it is not installed.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Optional SDK import
# ---------------------------------------------------------------------------
SDK_AVAILABLE = False
try:
    import claude_agent_sdk  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Execution mode enum
# ---------------------------------------------------------------------------


class SDKExecutionMode(Enum):
    """How the SDK agent should run.

    Attributes:
        TOOLS_ONLY: Use SDK-provided tools (Read, Bash, Glob) while keeping
            attune LLM routing for the main conversation.
        FULL_SDK: Let the SDK manage the entire agent lifecycle including
            conversation, tool calls, and subagent delegation.

    """

    TOOLS_ONLY = "tools_only"
    FULL_SDK = "full_sdk"


# ---------------------------------------------------------------------------
# SDK agent result
# ---------------------------------------------------------------------------


@dataclass
class SDKAgentResult:
    """Result from an SDKAgent execution.

    Mirrors the shape of ``ReleaseAgentResult`` / ``CDSAgentResult`` so that
    downstream consumers (quality gates, team aggregation) can handle any
    agent type uniformly.

    Args:
        agent_id: Unique identifier for the agent instance.
        role: Human-readable role name.
        success: Whether the execution succeeded.
        tier_used: Model tier used (cheap / capable / premium).
        mode: SDK execution mode that was used.
        findings: Dict of structured findings produced by the agent.
        score: Quality score (0-100).
        confidence: Confidence in the score (0.0-1.0).
        cost: Total LLM cost in USD.
        execution_time_ms: Wall-clock execution time in milliseconds.
        escalated: Whether tier escalation occurred.
        sdk_used: Whether the Agent SDK was actually invoked.
        error: Error message if the execution failed.

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
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation of this result.

        """
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
        """Deserialize from a dict.

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Reconstructed SDKAgentResult.

        """
        mode_str = data.get("mode", SDKExecutionMode.TOOLS_ONLY.value)
        try:
            mode = SDKExecutionMode(mode_str)
        except ValueError:
            mode = SDKExecutionMode.TOOLS_ONLY

        return cls(
            agent_id=data.get("agent_id", ""),
            role=data.get("role", ""),
            success=data.get("success", False),
            tier_used=data.get("tier_used", "cheap"),
            mode=mode,
            findings=data.get("findings", {}),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            cost=data.get("cost", 0.0),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            escalated=data.get("escalated", False),
            sdk_used=data.get("sdk_used", False),
            error=data.get("error"),
        )
