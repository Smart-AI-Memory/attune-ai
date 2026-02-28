"""Data models for persistent agent state.

Dataclasses for tracking agent execution history, accumulated metrics,
and checkpoint data for restart recovery.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentExecutionRecord:
    """Single execution record for an agent.

    Attributes:
        execution_id: Unique execution identifier
        agent_id: Agent that performed the execution
        role: Human-readable agent role
        started_at: ISO-format start timestamp
        completed_at: ISO-format completion timestamp (None if still running)
        status: Execution status (running, completed, failed, interrupted)
        tier_used: Final model tier used
        input_summary: Brief description of input
        findings: Structured findings dict
        score: Numeric score from agent
        confidence: Confidence in result (0.0-1.0)
        cost: LLM API cost in USD
        execution_time_ms: Wall-clock time in milliseconds
        error: Error message if failed

    """

    execution_id: str
    agent_id: str
    role: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    status: str = "running"
    tier_used: str = "cheap"
    input_summary: str = ""
    findings: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    cost: float = 0.0
    execution_time_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "tier_used": self.tier_used,
            "input_summary": self.input_summary,
            "findings": self.findings,
            "score": self.score,
            "confidence": self.confidence,
            "cost": self.cost,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentExecutionRecord:
        """Create from dictionary."""
        return cls(
            execution_id=data["execution_id"],
            agent_id=data["agent_id"],
            role=data["role"],
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            status=data.get("status", "running"),
            tier_used=data.get("tier_used", "cheap"),
            input_summary=data.get("input_summary", ""),
            findings=data.get("findings", {}),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            cost=data.get("cost", 0.0),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            error=data.get("error"),
        )


@dataclass
class AgentStateRecord:
    """Persistent state for a single agent identity.

    Tracks the full lifecycle history across multiple executions,
    including accumulated metrics and checkpoint data for recovery.

    Attributes:
        agent_id: Unique agent identifier
        role: Human-readable agent role
        created_at: ISO-format creation timestamp
        last_active: ISO-format timestamp of last activity
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        total_cost: Accumulated LLM API cost in USD
        accumulated_metrics: Rolling metric aggregates
        execution_history: List of execution records (trimmed to max size)
        last_checkpoint: Arbitrary state dict for restart recovery

    """

    agent_id: str
    role: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str | None = None
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_cost: float = 0.0
    accumulated_metrics: dict[str, float] = field(default_factory=dict)
    execution_history: list[AgentExecutionRecord] = field(default_factory=list)
    last_checkpoint: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate across all executions."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def avg_cost(self) -> float:
        """Calculate average cost per execution."""
        if self.total_executions == 0:
            return 0.0
        return self.total_cost / self.total_executions

    @property
    def avg_score(self) -> float:
        """Calculate average score from execution history."""
        completed = [e for e in self.execution_history if e.status == "completed"]
        if not completed:
            return 0.0
        return sum(e.score for e in completed) / len(completed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "total_cost": self.total_cost,
            "accumulated_metrics": self.accumulated_metrics,
            "execution_history": [e.to_dict() for e in self.execution_history],
            "last_checkpoint": self.last_checkpoint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentStateRecord:
        """Create from dictionary."""
        history = [AgentExecutionRecord.from_dict(e) for e in data.get("execution_history", [])]
        return cls(
            agent_id=data["agent_id"],
            role=data["role"],
            created_at=data.get("created_at", ""),
            last_active=data.get("last_active"),
            total_executions=data.get("total_executions", 0),
            successful_executions=data.get("successful_executions", 0),
            failed_executions=data.get("failed_executions", 0),
            total_cost=data.get("total_cost", 0.0),
            accumulated_metrics=data.get("accumulated_metrics", {}),
            execution_history=history,
            last_checkpoint=data.get("last_checkpoint", {}),
        )
