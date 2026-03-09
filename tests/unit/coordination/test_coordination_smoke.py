"""Smoke tests for coordination.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.coordination

        assert attune.coordination is not None

    def test_conflict_resolution_imports(self) -> None:
        """Test that conflict resolution classes import."""
        from attune.coordination import (
            ConflictResolver,
            ResolutionResult,
            ResolutionStrategy,
            TeamPriorities,
        )

        assert ConflictResolver is not None
        assert ResolutionResult is not None
        assert ResolutionStrategy is not None
        assert TeamPriorities is not None

    def test_agent_coordinator_imports(self) -> None:
        """Test that AgentCoordinator and AgentTask import."""
        from attune.coordination import AgentCoordinator, AgentTask

        assert AgentCoordinator is not None
        assert AgentTask is not None

    def test_team_session_imports(self) -> None:
        """Test that TeamSession imports."""
        from attune.coordination import TeamSession

        assert TeamSession is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_conflict_resolver_defaults(self) -> None:
        """Test ConflictResolver with defaults."""
        from attune.coordination import ConflictResolver

        resolver = ConflictResolver()
        assert resolver is not None

    def test_team_priorities_defaults(self) -> None:
        """Test TeamPriorities with defaults."""
        from attune.coordination import TeamPriorities

        priorities = TeamPriorities()
        assert priorities.readability_weight == 0.3
        assert priorities.security_weight == 0.3

    def test_resolution_strategy_enum(self) -> None:
        """Test ResolutionStrategy enum values."""
        from attune.coordination import ResolutionStrategy

        assert ResolutionStrategy.HIGHEST_CONFIDENCE.value == "highest_confidence"
        assert ResolutionStrategy.WEIGHTED_SCORE.value == "weighted_score"

    def test_agent_task_creation(self) -> None:
        """Test AgentTask dataclass creation."""
        from attune.coordination import AgentTask

        task = AgentTask(
            task_id="task-001",
            task_type="code_review",
            description="Review auth module",
            priority=8,
        )
        assert task.status == "pending"
        assert task.assigned_to is None
