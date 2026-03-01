"""Data classes for execution strategy results.

This module contains the core data structures used across all execution strategies:
- AgentResult: Result from individual agent execution
- StrategyResult: Aggregated result from strategy execution

Extracted from execution_strategies.py for improved maintainability.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Result from agent execution.

    Attributes:
        agent_id: ID of agent that produced result
        success: Whether execution succeeded
        output: Agent output data
        confidence: Confidence score (0-1)
        duration_seconds: Execution time
        error: Error message if failed

    """

    agent_id: str
    success: bool
    output: dict[str, Any]
    confidence: float = 0.0
    duration_seconds: float = 0.0
    error: str = ""


@dataclass
class StrategyResult:
    """Aggregated result from strategy execution.

    Attributes:
        success: Whether overall execution succeeded
        outputs: List of individual agent results
        aggregated_output: Combined/synthesized output
        total_duration: Total execution time
        errors: List of errors encountered

    """

    success: bool
    outputs: list[AgentResult]
    aggregated_output: dict[str, Any]
    total_duration: float = 0.0
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize errors list if None."""
        if not self.errors:
            self.errors = []


__all__ = ["AgentResult", "StrategyResult"]
