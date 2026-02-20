"""Data models for the Pattern Learning System.

Defines ExecutionRecord, PatternStats, and ContextSignature
dataclasses used by the learning grammar system.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutionRecord:
    """Record of a single pattern execution.

    Captures the essential metrics for learning.

    Attributes:
        pattern: Pattern/strategy name used
        success: Whether execution succeeded
        duration_seconds: Execution time
        cost: Estimated cost (tokens * rate)
        confidence: Aggregate confidence score
        context_features: Key features of the execution context
        timestamp: When the execution occurred
    """

    pattern: str
    success: bool
    duration_seconds: float
    cost: float = 0.0
    confidence: float = 0.0
    context_features: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionRecord:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class PatternStats:
    """Aggregated statistics for a pattern.

    Attributes:
        pattern: Pattern/strategy name
        total_executions: Number of times executed
        success_count: Number of successful executions
        total_duration: Sum of all execution durations
        total_cost: Sum of all execution costs
        avg_confidence: Average confidence across executions
    """

    pattern: str
    total_executions: int = 0
    success_count: int = 0
    total_duration: float = 0.0
    total_cost: float = 0.0
    avg_confidence: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 - 1.0)."""
        if self.total_executions == 0:
            return 0.0
        return self.success_count / self.total_executions

    @property
    def avg_duration(self) -> float:
        """Calculate average execution duration."""
        if self.total_executions == 0:
            return 0.0
        return self.total_duration / self.total_executions

    @property
    def avg_cost(self) -> float:
        """Calculate average execution cost."""
        if self.total_executions == 0:
            return 0.0
        return self.total_cost / self.total_executions

    def update(self, record: ExecutionRecord) -> None:
        """Update stats with a new execution record.

        Args:
            record: Execution record to incorporate
        """
        self.total_executions += 1
        if record.success:
            self.success_count += 1
        self.total_duration += record.duration_seconds
        self.total_cost += record.cost

        # Running average for confidence
        n = self.total_executions
        self.avg_confidence = (self.avg_confidence * (n - 1) + record.confidence) / n

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern": self.pattern,
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "total_duration": self.total_duration,
            "total_cost": self.total_cost,
            "avg_confidence": self.avg_confidence,
            # Computed properties
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "avg_cost": self.avg_cost,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PatternStats:
        """Create from dictionary."""
        return cls(
            pattern=data["pattern"],
            total_executions=data.get("total_executions", 0),
            success_count=data.get("success_count", 0),
            total_duration=data.get("total_duration", 0.0),
            total_cost=data.get("total_cost", 0.0),
            avg_confidence=data.get("avg_confidence", 0.0),
        )


@dataclass
class ContextSignature:
    """Signature of a context for similarity matching.

    Extracts key features from execution context for comparison.

    Attributes:
        task_type: Type of task (e.g., "code_review", "test_gen")
        agent_count: Number of agents involved
        has_conditions: Whether conditionals were used
        has_nesting: Whether nested workflows were used
        priority: Task priority level
    """

    task_type: str = ""
    agent_count: int = 0
    has_conditions: bool = False
    has_nesting: bool = False
    priority: str = "normal"

    @classmethod
    def from_context(cls, context: dict[str, Any]) -> ContextSignature:
        """Extract signature from execution context.

        Args:
            context: Execution context dictionary

        Returns:
            ContextSignature with extracted features
        """
        return cls(
            task_type=context.get("task_type", context.get("_task_type", "")),
            agent_count=len(context.get("agents", [])),
            has_conditions="_conditional" in context,
            has_nesting="_nesting" in context,
            priority=context.get("priority", "normal"),
        )

    def similarity(self, other: ContextSignature) -> float:
        """Calculate similarity score with another signature.

        Args:
            other: Signature to compare with

        Returns:
            Similarity score (0.0 - 1.0)
        """
        score = 0.0
        max_score = 0.0

        # Task type match (highest weight)
        max_score += 3.0
        if self.task_type and other.task_type:
            if self.task_type == other.task_type:
                score += 3.0
            elif self.task_type.split("_")[0] == other.task_type.split("_")[0]:
                score += 1.5  # Partial match

        # Agent count similarity
        max_score += 1.0
        if self.agent_count > 0 and other.agent_count > 0:
            ratio = min(self.agent_count, other.agent_count) / max(
                self.agent_count, other.agent_count
            )
            score += ratio

        # Boolean features
        max_score += 2.0
        if self.has_conditions == other.has_conditions:
            score += 1.0
        if self.has_nesting == other.has_nesting:
            score += 1.0

        # Priority match
        max_score += 1.0
        if self.priority == other.priority:
            score += 1.0

        return score / max_score if max_score > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextSignature:
        """Create from dictionary."""
        return cls(**data)
