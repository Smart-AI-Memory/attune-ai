"""A/B Testing Data Structures

Data models for A/B testing experiments including variants,
experiments, and result summaries.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExperimentStatus(Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class AllocationStrategy(Enum):
    """Strategy for allocating traffic to variants."""

    FIXED = "fixed"  # Fixed percentage split
    EPSILON_GREEDY = "epsilon_greedy"  # Explore vs exploit
    THOMPSON_SAMPLING = "thompson_sampling"  # Bayesian bandits
    UCB = "ucb"  # Upper confidence bound


@dataclass
class Variant:
    """A variant in an A/B experiment."""

    variant_id: str
    name: str
    description: str
    config: dict[str, Any]
    is_control: bool = False
    traffic_percentage: float = 50.0

    # Statistics
    impressions: int = 0
    conversions: int = 0
    total_success_score: float = 0.0

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate."""
        if self.impressions == 0:
            return 0.0
        return self.conversions / self.impressions

    @property
    def avg_success_score(self) -> float:
        """Calculate average success score."""
        if self.impressions == 0:
            return 0.0
        return self.total_success_score / self.impressions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "is_control": self.is_control,
            "traffic_percentage": self.traffic_percentage,
            "impressions": self.impressions,
            "conversions": self.conversions,
            "total_success_score": self.total_success_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Variant:
        """Create from dictionary."""
        return cls(
            variant_id=data["variant_id"],
            name=data["name"],
            description=data["description"],
            config=data["config"],
            is_control=data.get("is_control", False),
            traffic_percentage=data.get("traffic_percentage", 50.0),
            impressions=data.get("impressions", 0),
            conversions=data.get("conversions", 0),
            total_success_score=data.get("total_success_score", 0.0),
        )


@dataclass
class Experiment:
    """An A/B experiment definition."""

    experiment_id: str
    name: str
    description: str
    hypothesis: str
    variants: list[Variant]
    domain_filter: str | None = None
    goal_filter: str | None = None
    allocation_strategy: AllocationStrategy = AllocationStrategy.FIXED
    min_sample_size: int = 100
    max_duration_days: int = 30
    confidence_level: float = 0.95
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "variants": [v.to_dict() for v in self.variants],
            "domain_filter": self.domain_filter,
            "goal_filter": self.goal_filter,
            "allocation_strategy": self.allocation_strategy.value,
            "min_sample_size": self.min_sample_size,
            "max_duration_days": self.max_duration_days,
            "confidence_level": self.confidence_level,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Experiment:
        """Create from dictionary."""
        return cls(
            experiment_id=data["experiment_id"],
            name=data["name"],
            description=data["description"],
            hypothesis=data["hypothesis"],
            variants=[Variant.from_dict(v) for v in data["variants"]],
            domain_filter=data.get("domain_filter"),
            goal_filter=data.get("goal_filter"),
            allocation_strategy=AllocationStrategy(data.get("allocation_strategy", "fixed")),
            min_sample_size=data.get("min_sample_size", 100),
            max_duration_days=data.get("max_duration_days", 30),
            confidence_level=data.get("confidence_level", 0.95),
            status=ExperimentStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            ended_at=(datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None),
        )

    @property
    def total_impressions(self) -> int:
        """Total impressions across all variants."""
        return sum(v.impressions for v in self.variants)

    @property
    def control(self) -> Variant | None:
        """Get control variant."""
        for v in self.variants:
            if v.is_control:
                return v
        return None

    @property
    def treatments(self) -> list[Variant]:
        """Get treatment variants (non-control)."""
        return [v for v in self.variants if not v.is_control]


@dataclass
class ExperimentResult:
    """Results and analysis of an experiment."""

    experiment: Experiment
    winner: Variant | None
    is_significant: bool
    p_value: float
    confidence_interval: tuple[float, float]
    lift: float  # Percentage improvement over control
    recommendation: str
