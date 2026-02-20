"""Data models for Agent-to-LLM Feedback Loop.

Defines:
- ModelTier: Model tier enum
- FeedbackEntry: Quality feedback for an LLM response
- QualityStats: Quality statistics for a workflow stage
- TierRecommendation: Tier recommendation based on feedback

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ModelTier(str, Enum):
    """Model tier enum matching workflows.base.ModelTier."""

    CHEAP = "cheap"
    CAPABLE = "capable"
    PREMIUM = "premium"


@dataclass
class FeedbackEntry:
    """Quality feedback for an LLM response.

    Represents a single quality rating for a workflow stage execution.
    """

    feedback_id: str
    workflow_name: str
    stage_name: str
    tier: str  # ModelTier value
    quality_score: float  # 0.0 (bad) to 1.0 (excellent)
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "workflow_name": self.workflow_name,
            "stage_name": self.stage_name,
            "tier": self.tier,
            "quality_score": self.quality_score,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackEntry:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()

        # Handle missing feedback_id (legacy entries)
        feedback_id = data.get("feedback_id")
        if not feedback_id:
            feedback_id = f"fb-{int(timestamp.timestamp()*1000)}"

        return cls(
            feedback_id=feedback_id,
            workflow_name=data["workflow_name"],
            stage_name=data["stage_name"],
            tier=data["tier"],
            quality_score=data["quality_score"],
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


@dataclass
class QualityStats:
    """Quality statistics for a workflow stage."""

    workflow_name: str
    stage_name: str
    tier: str
    avg_quality: float
    min_quality: float
    max_quality: float
    sample_count: int
    recent_trend: float  # -1.0 (declining) to 1.0 (improving)


@dataclass
class TierRecommendation:
    """Tier recommendation based on quality feedback."""

    current_tier: str
    recommended_tier: str
    confidence: float  # 0.0 (low) to 1.0 (high)
    reason: str
    stats: dict[str, QualityStats]  # Stats by tier
