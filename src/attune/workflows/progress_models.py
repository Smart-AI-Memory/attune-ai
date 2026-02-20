"""Progress Tracking Data Models

Data classes and enums for the progress tracking system.
Provides ProgressStatus, StageProgress, ProgressUpdate, and callback type aliases.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProgressStatus(Enum):
    """Status of a workflow or stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FALLBACK = "fallback"  # Using fallback model
    RETRYING = "retrying"  # Retrying after error


@dataclass
class StageProgress:
    """Progress information for a single stage."""

    name: str
    status: ProgressStatus
    tier: str = "capable"
    model: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None
    fallback_info: str | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "tier": self.tier,
            "model": self.model,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "cost": self.cost,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "error": self.error,
            "fallback_info": self.fallback_info,
            "retry_count": self.retry_count,
        }


@dataclass
class ProgressUpdate:
    """A progress update to be broadcast."""

    workflow: str
    workflow_id: str
    current_stage: str
    stage_index: int
    total_stages: int
    status: ProgressStatus
    message: str
    cost_so_far: float = 0.0
    tokens_so_far: int = 0
    percent_complete: float = 0.0
    estimated_remaining_ms: int | None = None
    stages: list[StageProgress] = field(default_factory=list)
    fallback_info: str | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "workflow": self.workflow,
            "workflow_id": self.workflow_id,
            "current_stage": self.current_stage,
            "stage_index": self.stage_index,
            "total_stages": self.total_stages,
            "status": self.status.value,
            "message": self.message,
            "cost_so_far": self.cost_so_far,
            "tokens_so_far": self.tokens_so_far,
            "percent_complete": self.percent_complete,
            "estimated_remaining_ms": self.estimated_remaining_ms,
            "stages": [s.to_dict() for s in self.stages],
            "fallback_info": self.fallback_info,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# Type for progress callbacks
ProgressCallback = Callable[[ProgressUpdate], None]
AsyncProgressCallback = Callable[[ProgressUpdate], Coroutine[Any, Any, None]]
