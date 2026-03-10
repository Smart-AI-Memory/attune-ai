"""Smoke tests for attune.coordination module."""


class TestCoordinationImports:
    """Verify the coordination package exports are importable."""

    def test_import_package(self):
        """Test that the coordination package imports cleanly."""
        from attune.coordination import (
            AgentCoordinator,
            ConflictResolver,
            TeamSession,
        )

        assert ConflictResolver is not None
        assert AgentCoordinator is not None
        assert TeamSession is not None

    def test_resolution_strategy_enum(self):
        """Test ResolutionStrategy enum values."""
        from attune.coordination.conflict_resolution import ResolutionStrategy

        assert ResolutionStrategy.HIGHEST_CONFIDENCE.value == "highest_confidence"
        assert ResolutionStrategy.WEIGHTED_SCORE.value == "weighted_score"

    def test_team_priorities_defaults(self):
        """Test TeamPriorities default weights."""
        from attune.coordination.conflict_resolution import TeamPriorities

        tp = TeamPriorities()
        total = (
            tp.readability_weight
            + tp.performance_weight
            + tp.security_weight
            + tp.maintainability_weight
        )
        assert abs(total - 1.0) < 0.01

    def test_agent_task_dataclass(self):
        """Test AgentTask instantiation."""
        from attune.coordination.agent_coordinator import AgentTask

        task = AgentTask(
            task_id="t-001",
            task_type="code_review",
            description="Review auth module",
            priority=8,
        )
        assert task.status == "pending"
        assert task.assigned_to is None

    def test_conflict_resolver_instantiation(self):
        """Test ConflictResolver can be created."""
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        assert resolver is not None
