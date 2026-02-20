"""Data models for vector embeddings.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmbeddedGoal:
    """A goal with its embedding vector and metadata."""

    goal_id: str
    goal_text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    domains: list[str] = field(default_factory=list)
    workflow_id: str | None = None
    success_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "goal_id": self.goal_id,
            "goal_text": self.goal_text,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "domains": self.domains,
            "workflow_id": self.workflow_id,
            "success_score": self.success_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddedGoal:
        """Create from dictionary."""
        return cls(
            goal_id=data["goal_id"],
            goal_text=data["goal_text"],
            embedding=data["embedding"],
            metadata=data.get("metadata", {}),
            domains=data.get("domains", []),
            workflow_id=data.get("workflow_id"),
            success_score=data.get("success_score", 0.0),
        )


@dataclass
class SimilarityResult:
    """Result of a similarity search."""

    goal: EmbeddedGoal
    similarity: float
    rank: int
