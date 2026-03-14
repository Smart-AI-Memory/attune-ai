"""Tests for coordination.py and workflows/release_prep.py

Comprehensive tests targeting maximum statement coverage for:
1. ConflictResolver, AgentCoordinator, TeamSession (coordination.py)
2. ReleasePreparationWorkflow, format_release_prep_report (release_prep.py)

All external dependencies (LLM calls, Redis, subprocess, imports) are mocked.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from attune.coordination import (
    AgentCoordinator,
    AgentTask,
    ConflictResolver,
    ResolutionResult,
    ResolutionStrategy,
    TeamPriorities,
    TeamSession,
)

# ---------------------------------------------------------------------------
# Coordination module imports
# ---------------------------------------------------------------------------
from attune.pattern_library import Pattern

# ---------------------------------------------------------------------------
# Release-prep imports – mock heavy base-class machinery
# ---------------------------------------------------------------------------
from attune.workflows.release_prep import (
    RELEASE_PREP_STEPS,
    ReleasePreparationWorkflow,
    format_release_prep_report,
)

# ===================================================================
# Helpers / Fixtures
# ===================================================================


def _make_pattern(
    id: str = "p1",
    agent_id: str = "agent_a",
    pattern_type: str = "best_practice",
    name: str = "Pattern 1",
    description: str = "A test pattern",
    confidence: float = 0.8,
    usage_count: int = 10,
    success_count: int = 8,
    failure_count: int = 2,
    discovered_at: datetime | None = None,
    context: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Pattern:
    """Build a Pattern with sensible defaults for testing."""
    return Pattern(
        id=id,
        agent_id=agent_id,
        pattern_type=pattern_type,
        name=name,
        description=description,
        confidence=confidence,
        usage_count=usage_count,
        success_count=success_count,
        failure_count=failure_count,
        discovered_at=discovered_at or datetime.now(),
        context=context or {},
        tags=tags or [],
    )


@pytest.fixture
def resolver() -> ConflictResolver:
    """Return a fresh ConflictResolver with default settings."""
    return ConflictResolver()


@pytest.fixture
def two_patterns() -> list[Pattern]:
    """Two conflicting patterns with differing characteristics."""
    return [
        _make_pattern(
            id="p_high_conf",
            name="High Confidence",
            confidence=0.95,
            usage_count=20,
            success_count=18,
            failure_count=2,
            pattern_type="security",
            tags=["security", "auth"],
            context={"language": "python", "framework": "django"},
        ),
        _make_pattern(
            id="p_low_conf",
            name="Low Confidence",
            confidence=0.50,
            usage_count=5,
            success_count=2,
            failure_count=3,
            pattern_type="style",
            tags=["style"],
            context={"language": "python"},
        ),
    ]


@pytest.fixture
def mock_memory() -> MagicMock:
    """Return a mock short-term memory object for coordinator tests."""
    mem = MagicMock()
    mem.stash.return_value = True
    mem.retrieve.return_value = None
    mem.send_signal.return_value = True
    mem.receive_signals.return_value = []
    mem.create_session.return_value = True
    mem.join_session.return_value = True
    mem.get_session.return_value = {"purpose": "test", "agents": []}
    return mem


# ===================================================================
# Tests: ResolutionStrategy / data classes
# ===================================================================


class TestResolutionStrategy:
    """Tests for the ResolutionStrategy enum."""

    def test_all_strategy_values(self) -> None:
        """Verify all strategy enum members exist."""
        assert ResolutionStrategy.HIGHEST_CONFIDENCE.value == "highest_confidence"
        assert ResolutionStrategy.MOST_RECENT.value == "most_recent"
        assert ResolutionStrategy.BEST_CONTEXT_MATCH.value == "best_context_match"
        assert ResolutionStrategy.TEAM_PRIORITY.value == "team_priority"
        assert ResolutionStrategy.WEIGHTED_SCORE.value == "weighted_score"


class TestResolutionResult:
    """Tests for the ResolutionResult dataclass."""

    def test_fields_present(self, two_patterns: list[Pattern]) -> None:
        """Verify all fields are accessible."""
        result = ResolutionResult(
            winning_pattern=two_patterns[0],
            losing_patterns=[two_patterns[1]],
            strategy_used=ResolutionStrategy.HIGHEST_CONFIDENCE,
            confidence=0.95,
            reasoning="Highest confidence wins",
            factors={"confidence": 0.95},
        )
        assert result.winning_pattern.id == "p_high_conf"
        assert len(result.losing_patterns) == 1
        assert result.confidence == 0.95
        assert result.reasoning == "Highest confidence wins"
        assert "confidence" in result.factors


class TestTeamPriorities:
    """Tests for the TeamPriorities dataclass."""

    def test_default_values(self) -> None:
        """Verify default weights and preferences."""
        tp = TeamPriorities()
        assert tp.readability_weight == 0.3
        assert tp.performance_weight == 0.2
        assert tp.security_weight == 0.3
        assert tp.maintainability_weight == 0.2
        assert "security" in tp.type_preferences
        assert tp.preferred_tags == []

    def test_custom_values(self) -> None:
        """Verify custom initialization."""
        tp = TeamPriorities(
            readability_weight=0.5,
            preferred_tags=["perf", "security"],
        )
        assert tp.readability_weight == 0.5
        assert "perf" in tp.preferred_tags


# ===================================================================
# Tests: ConflictResolver
# ===================================================================


class TestConflictResolver:
    """Tests for ConflictResolver."""

    def test_init_defaults(self) -> None:
        """Default strategy and priorities are set."""
        cr = ConflictResolver()
        assert cr.default_strategy == ResolutionStrategy.WEIGHTED_SCORE
        assert isinstance(cr.team_priorities, TeamPriorities)
        assert cr.resolution_history == []

    def test_init_custom_strategy(self) -> None:
        """Custom default strategy is respected."""
        cr = ConflictResolver(default_strategy=ResolutionStrategy.MOST_RECENT)
        assert cr.default_strategy == ResolutionStrategy.MOST_RECENT

    def test_init_custom_priorities(self) -> None:
        """Custom team priorities are stored."""
        tp = TeamPriorities(readability_weight=0.9)
        cr = ConflictResolver(team_priorities=tp)
        assert cr.team_priorities.readability_weight == 0.9

    def test_resolve_too_few_patterns_raises(self, resolver: ConflictResolver) -> None:
        """Resolving fewer than 2 patterns raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            resolver.resolve_patterns([_make_pattern()])

    def test_resolve_empty_list_raises(self, resolver: ConflictResolver) -> None:
        """Empty pattern list raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            resolver.resolve_patterns([])

    # ---------- Strategy: HIGHEST_CONFIDENCE ----------

    def test_resolve_highest_confidence(
        self,
        resolver: ConflictResolver,
        two_patterns: list[Pattern],
    ) -> None:
        """Highest confidence pattern should win."""
        result = resolver.resolve_patterns(
            two_patterns,
            strategy=ResolutionStrategy.HIGHEST_CONFIDENCE,
        )
        assert result.winning_pattern.id == "p_high_conf"
        assert result.strategy_used == ResolutionStrategy.HIGHEST_CONFIDENCE
        assert result.confidence == pytest.approx(0.95)
        assert "confidence" in result.reasoning.lower() or "Highest" in result.reasoning

    # ---------- Strategy: MOST_RECENT ----------

    def test_resolve_most_recent(self, resolver: ConflictResolver) -> None:
        """Most recent pattern should win with MOST_RECENT strategy."""
        old = _make_pattern(
            id="old",
            name="Old",
            discovered_at=datetime.now() - timedelta(days=300),
        )
        new = _make_pattern(
            id="new",
            name="New",
            discovered_at=datetime.now() - timedelta(days=1),
        )
        result = resolver.resolve_patterns(
            [old, new],
            strategy=ResolutionStrategy.MOST_RECENT,
        )
        assert result.winning_pattern.id == "new"
        assert "most recent" in result.reasoning.lower() or "New" in result.reasoning

    # ---------- Strategy: BEST_CONTEXT_MATCH ----------

    def test_resolve_best_context_match(self, resolver: ConflictResolver) -> None:
        """Pattern with better context overlap wins."""
        p1 = _make_pattern(
            id="match",
            name="Good Match",
            context={"language": "python", "level": "senior"},
            tags=["python"],
        )
        p2 = _make_pattern(
            id="nomatch",
            name="No Match",
            context={"language": "rust"},
            tags=["rust"],
        )
        result = resolver.resolve_patterns(
            [p1, p2],
            context={"language": "python", "level": "senior", "tags": ["python"]},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        assert result.winning_pattern.id == "match"

    # ---------- Strategy: TEAM_PRIORITY ----------

    def test_resolve_team_priority(self) -> None:
        """Security pattern wins when team priority is security."""
        tp = TeamPriorities(preferred_tags=["security"])
        cr = ConflictResolver(team_priorities=tp)
        sec = _make_pattern(
            id="sec",
            name="Security Pattern",
            pattern_type="security",
            tags=["security"],
        )
        style = _make_pattern(
            id="sty",
            name="Style Pattern",
            pattern_type="style",
            tags=["style"],
        )
        result = cr.resolve_patterns(
            [sec, style],
            context={"team_priority": "security"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.winning_pattern.id == "sec"

    def test_resolve_team_priority_readability(self) -> None:
        """Style/best_practice wins when team priority is readability."""
        cr = ConflictResolver()
        readable = _make_pattern(
            id="read",
            name="Readable",
            pattern_type="style",
            tags=["readability"],
        )
        perf = _make_pattern(
            id="perf",
            name="Performance",
            pattern_type="performance",
            tags=[],
        )
        result = cr.resolve_patterns(
            [readable, perf],
            context={"team_priority": "readability"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.winning_pattern.id == "read"

    def test_resolve_team_priority_maintainability(self) -> None:
        """Best_practice pattern wins when priority is maintainability."""
        cr = ConflictResolver()
        bp = _make_pattern(
            id="bp",
            name="Best Practice",
            pattern_type="best_practice",
            tags=[],
        )
        other = _make_pattern(
            id="other",
            name="Other",
            pattern_type="warning",
            tags=[],
        )
        result = cr.resolve_patterns(
            [bp, other],
            context={"team_priority": "maintainability"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.winning_pattern.id == "bp"

    # ---------- Strategy: WEIGHTED_SCORE ----------

    def test_resolve_weighted_score(
        self,
        resolver: ConflictResolver,
        two_patterns: list[Pattern],
    ) -> None:
        """Weighted scoring uses default strategy."""
        result = resolver.resolve_patterns(two_patterns)
        assert result.strategy_used == ResolutionStrategy.WEIGHTED_SCORE
        assert result.winning_pattern.id == "p_high_conf"
        assert "weighted" in result.reasoning.lower()
        # Factors should contain all components
        assert "confidence" in result.factors
        assert "total" in result.factors

    def test_resolve_weighted_score_explicit(self, resolver: ConflictResolver) -> None:
        """Explicit WEIGHTED_SCORE strategy."""
        p1 = _make_pattern(
            id="a",
            name="A",
            confidence=0.9,
            usage_count=10,
            success_count=9,
            failure_count=1,
        )
        p2 = _make_pattern(
            id="b",
            name="B",
            confidence=0.3,
            usage_count=10,
            success_count=2,
            failure_count=8,
        )
        result = resolver.resolve_patterns(
            [p1, p2],
            strategy=ResolutionStrategy.WEIGHTED_SCORE,
        )
        assert result.winning_pattern.id == "a"

    # ---------- Context matching edge cases ----------

    def test_context_match_no_context(self, resolver: ConflictResolver) -> None:
        """No context on either side returns neutral score."""
        p1 = _make_pattern(id="a", name="A", context={})
        p2 = _make_pattern(id="b", name="B", context={})
        result = resolver.resolve_patterns(
            [p1, p2],
            context={},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        # Both should get 0.5 (neutral)
        assert result is not None

    def test_context_match_no_common_keys(self, resolver: ConflictResolver) -> None:
        """No common keys between context and pattern."""
        p1 = _make_pattern(id="a", name="A", context={"x": 1})
        p2 = _make_pattern(id="b", name="B", context={"y": 2})
        result = resolver.resolve_patterns(
            [p1, p2],
            context={"z": 3},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        assert result is not None

    def test_context_match_with_tags_overlap(self, resolver: ConflictResolver) -> None:
        """Tag overlap gives bonus score."""
        p1 = _make_pattern(
            id="tagged",
            name="Tagged",
            context={"lang": "python"},
            tags=["python", "web"],
        )
        p2 = _make_pattern(
            id="untagged",
            name="Untagged",
            context={"lang": "python"},
            tags=[],
        )
        result = resolver.resolve_patterns(
            [p1, p2],
            context={"lang": "python", "tags": ["python", "web"]},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        assert result.winning_pattern.id == "tagged"

    # ---------- Team alignment edge cases ----------

    def test_team_alignment_preferred_tags(self) -> None:
        """Preferred tags add a bonus."""
        tp = TeamPriorities(preferred_tags=["critical"])
        cr = ConflictResolver(team_priorities=tp)
        p1 = _make_pattern(id="crit", name="Critical", pattern_type="security", tags=["critical"])
        p2 = _make_pattern(id="norm", name="Normal", pattern_type="security", tags=["normal"])
        result = cr.resolve_patterns(
            [p1, p2],
            context={"team_priority": "security"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.winning_pattern.id == "crit"

    def test_team_alignment_no_priority(self, resolver: ConflictResolver) -> None:
        """No team priority in context still works."""
        p1 = _make_pattern(id="a", name="A", pattern_type="security")
        p2 = _make_pattern(id="b", name="B", pattern_type="style")
        result = resolver.resolve_patterns(
            [p1, p2],
            context={},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result is not None

    def test_team_alignment_performance_priority(self) -> None:
        """Performance priority boosts performance/optimization types."""
        cr = ConflictResolver()
        perf = _make_pattern(
            id="perf",
            name="Perf",
            pattern_type="performance",
            tags=["optimization"],
        )
        other = _make_pattern(id="other", name="Other", pattern_type="documentation", tags=[])
        result = cr.resolve_patterns(
            [perf, other],
            context={"team_priority": "performance"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.winning_pattern.id == "perf"

    # ---------- Success rate for unused patterns ----------

    def test_pattern_score_zero_usage(self, resolver: ConflictResolver) -> None:
        """Zero usage_count gives 0.5 default success_rate."""
        p = _make_pattern(usage_count=0, success_count=0, failure_count=0)
        score = resolver._calculate_pattern_score(p, {}, ResolutionStrategy.WEIGHTED_SCORE)
        assert score["success_rate"] == 0.5

    # ---------- Recency score ----------

    def test_recency_score_old_pattern(self, resolver: ConflictResolver) -> None:
        """Very old pattern gets low recency score."""
        old = _make_pattern(discovered_at=datetime.now() - timedelta(days=400))
        score = resolver._calculate_pattern_score(old, {}, ResolutionStrategy.WEIGHTED_SCORE)
        # 400 / 365 > 1, so max(0, 1 - 1.09) = 0
        assert score["recency"] == 0.0

    def test_recency_score_new_pattern(self, resolver: ConflictResolver) -> None:
        """Very new pattern gets high recency score."""
        new = _make_pattern(discovered_at=datetime.now())
        score = resolver._calculate_pattern_score(new, {}, ResolutionStrategy.WEIGHTED_SCORE)
        assert score["recency"] >= 0.99

    # ---------- Resolution history ----------

    def test_resolution_tracked_in_history(
        self,
        resolver: ConflictResolver,
        two_patterns: list[Pattern],
    ) -> None:
        """Each resolution is appended to history."""
        resolver.resolve_patterns(two_patterns)
        assert len(resolver.resolution_history) == 1
        resolver.resolve_patterns(two_patterns)
        assert len(resolver.resolution_history) == 2

    def test_clear_history(self, resolver: ConflictResolver, two_patterns: list[Pattern]) -> None:
        """clear_history empties the list."""
        resolver.resolve_patterns(two_patterns)
        resolver.clear_history()
        assert resolver.resolution_history == []

    # ---------- Resolution stats ----------

    def test_stats_empty_history(self, resolver: ConflictResolver) -> None:
        """Stats for empty history."""
        stats = resolver.get_resolution_stats()
        assert stats["total_resolutions"] == 0
        assert stats["strategies_used"] == {}
        assert stats["average_confidence"] == 0.0

    def test_stats_with_history(
        self,
        resolver: ConflictResolver,
        two_patterns: list[Pattern],
    ) -> None:
        """Stats reflect accumulated resolutions."""
        resolver.resolve_patterns(two_patterns, strategy=ResolutionStrategy.HIGHEST_CONFIDENCE)
        resolver.resolve_patterns(two_patterns, strategy=ResolutionStrategy.HIGHEST_CONFIDENCE)
        resolver.resolve_patterns(two_patterns, strategy=ResolutionStrategy.MOST_RECENT)
        stats = resolver.get_resolution_stats()
        assert stats["total_resolutions"] == 3
        assert stats["strategies_used"]["highest_confidence"] == 2
        assert stats["strategies_used"]["most_recent"] == 1
        assert stats["most_used_strategy"] == "highest_confidence"
        assert stats["average_confidence"] > 0

    # ---------- Reasoning generation ----------

    def test_reasoning_includes_loser_names(
        self,
        resolver: ConflictResolver,
        two_patterns: list[Pattern],
    ) -> None:
        """Reasoning mentions losing pattern names."""
        result = resolver.resolve_patterns(
            two_patterns,
            strategy=ResolutionStrategy.HIGHEST_CONFIDENCE,
        )
        assert "Low Confidence" in result.reasoning

    def test_reasoning_team_priority(self, resolver: ConflictResolver) -> None:
        """Team priority reasoning mentions the team priority."""
        p1 = _make_pattern(id="a", name="A", pattern_type="security")
        p2 = _make_pattern(id="b", name="B", pattern_type="style")
        result = resolver.resolve_patterns(
            [p1, p2],
            context={"team_priority": "security"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert "team priority" in result.reasoning.lower() or "security" in result.reasoning.lower()

    def test_reasoning_context_match(self, resolver: ConflictResolver) -> None:
        """Context match reasoning includes match score."""
        p1 = _make_pattern(id="a", name="A", context={"lang": "py"})
        p2 = _make_pattern(id="b", name="B", context={"lang": "js"})
        result = resolver.resolve_patterns(
            [p1, p2],
            context={"lang": "py"},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        assert "best match" in result.reasoning.lower() or "context" in result.reasoning.lower()

    def test_reasoning_most_recent(self, resolver: ConflictResolver) -> None:
        """Most recent reasoning mentions days ago."""
        p1 = _make_pattern(id="a", name="A", discovered_at=datetime.now())
        p2 = _make_pattern(id="b", name="B", discovered_at=datetime.now() - timedelta(days=30))
        result = resolver.resolve_patterns(
            [p1, p2],
            strategy=ResolutionStrategy.MOST_RECENT,
        )
        assert "days ago" in result.reasoning

    # ---------- Multiple patterns (>2) ----------

    def test_resolve_three_patterns(self, resolver: ConflictResolver) -> None:
        """Resolving more than 2 patterns works."""
        patterns = [
            _make_pattern(id="a", name="A", confidence=0.9),
            _make_pattern(id="b", name="B", confidence=0.7),
            _make_pattern(id="c", name="C", confidence=0.5),
        ]
        result = resolver.resolve_patterns(patterns, strategy=ResolutionStrategy.HIGHEST_CONFIDENCE)
        assert result.winning_pattern.id == "a"
        assert len(result.losing_patterns) == 2


# ===================================================================
# Tests: AgentTask dataclass
# ===================================================================


class TestAgentTask:
    """Tests for the AgentTask dataclass."""

    def test_default_values(self) -> None:
        """Default field values are set correctly."""
        task = AgentTask(
            task_id="t1",
            task_type="review",
            description="Review code",
        )
        assert task.assigned_to is None
        assert task.status == "pending"
        assert task.priority == 5
        assert task.context == {}
        assert task.result is None

    def test_custom_values(self) -> None:
        """Custom field values are preserved."""
        task = AgentTask(
            task_id="t2",
            task_type="audit",
            description="Security audit",
            assigned_to="agent_x",
            status="in_progress",
            priority=9,
            context={"scope": "full"},
            result={"issues": 3},
        )
        assert task.priority == 9
        assert task.result == {"issues": 3}


# ===================================================================
# Tests: AgentCoordinator
# ===================================================================


class TestAgentCoordinator:
    """Tests for the AgentCoordinator class."""

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_init(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Coordinator initializes with memory and team_id."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.team_id == "team1"
        assert coord.memory is mock_memory
        assert isinstance(coord.conflict_resolver, ConflictResolver)
        assert coord._active_agents == {}

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_init_custom_resolver(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Custom ConflictResolver is used when provided."""
        mock_tier.STEWARD = "steward"
        custom_resolver = ConflictResolver(default_strategy=ResolutionStrategy.MOST_RECENT)
        coord = AgentCoordinator(mock_memory, team_id="t", conflict_resolver=custom_resolver)
        assert coord.conflict_resolver is custom_resolver

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_add_task(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """add_task stashes task data and returns True."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = AgentTask(task_id="t1", task_type="review", description="Review code")
        result = coord.add_task(task)
        assert result is True
        mock_memory.stash.assert_called_once()
        call_args = mock_memory.stash.call_args
        assert call_args[0][0] == "task:team1:t1"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_add_task_failure(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """add_task returns False when stash returns falsy."""
        mock_tier.STEWARD = "steward"
        mock_memory.stash.return_value = False
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = AgentTask(task_id="t1", task_type="review", description="Review code")
        assert coord.add_task(task) is False

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_pending_tasks_empty(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """No pending tasks when signals return empty."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        tasks = coord.get_pending_tasks()
        assert tasks == []

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_pending_tasks_filters_by_type(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """get_pending_tasks filters by task_type when specified."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "t1",
                    "task_type": "review",
                    "description": "Review",
                    "status": "pending",
                    "priority": 8,
                    "context": {},
                },
            },
            {
                "data": {
                    "task_id": "t2",
                    "task_type": "audit",
                    "description": "Audit",
                    "status": "pending",
                    "priority": 5,
                    "context": {},
                },
            },
        ]
        coord = AgentCoordinator(mock_memory, team_id="team1")
        # Filter by review type
        tasks = coord.get_pending_tasks(task_type="review")
        assert len(tasks) == 1
        assert tasks[0].task_id == "t1"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_pending_tasks_sorted_by_priority(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Pending tasks are sorted by priority (highest first)."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "low",
                    "task_type": "review",
                    "description": "Low",
                    "status": "pending",
                    "priority": 2,
                },
            },
            {
                "data": {
                    "task_id": "high",
                    "task_type": "review",
                    "description": "High",
                    "status": "pending",
                    "priority": 9,
                },
            },
        ]
        coord = AgentCoordinator(mock_memory, team_id="team1")
        tasks = coord.get_pending_tasks()
        assert tasks[0].task_id == "high"
        assert tasks[1].task_id == "low"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_pending_tasks_skips_non_pending(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Non-pending tasks are excluded."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "done",
                    "task_type": "review",
                    "description": "Done",
                    "status": "completed",
                    "priority": 5,
                },
            },
        ]
        coord = AgentCoordinator(mock_memory, team_id="team1")
        tasks = coord.get_pending_tasks()
        assert len(tasks) == 0

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_claim_task_success(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Agent can claim an available pending task."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "t1",
                    "task_type": "review",
                    "description": "Review",
                    "status": "pending",
                    "priority": 5,
                },
            },
        ]
        mock_memory.retrieve.return_value = {"status": "pending", "task_type": "review"}
        mock_memory.stash.return_value = True
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = coord.claim_task("agent_1")
        assert task is not None
        assert task.status == "in_progress"
        assert task.assigned_to == "agent_1"
        mock_memory.send_signal.assert_called()

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_claim_task_none_available(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Returns None when no tasks are pending."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = coord.claim_task("agent_1")
        assert task is None

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_claim_task_already_claimed(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Returns None when task is already in_progress (not pending)."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "t1",
                    "task_type": "review",
                    "description": "Review",
                    "status": "pending",
                    "priority": 5,
                },
            },
        ]
        # retrieve returns non-pending status
        mock_memory.retrieve.return_value = {"status": "in_progress"}
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = coord.claim_task("agent_2")
        assert task is None

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_claim_task_stash_failure(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Returns None when stash fails during claim."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "t1",
                    "task_type": "review",
                    "description": "Review",
                    "status": "pending",
                    "priority": 5,
                },
            },
        ]
        mock_memory.retrieve.return_value = {"status": "pending"}
        mock_memory.stash.return_value = False
        coord = AgentCoordinator(mock_memory, team_id="team1")
        task = coord.claim_task("agent_1")
        assert task is None

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_complete_task_success(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Completing a task updates status and broadcasts."""
        mock_tier.STEWARD = "steward"
        mock_memory.retrieve.return_value = {
            "status": "in_progress",
            "assigned_to": "agent_1",
            "task_type": "review",
        }
        mock_memory.stash.return_value = True
        coord = AgentCoordinator(mock_memory, team_id="team1")
        result = coord.complete_task("t1", {"issues": 3}, agent_id="agent_1")
        assert result is True
        mock_memory.send_signal.assert_called()

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_complete_task_not_found(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Completing a non-existent task returns False."""
        mock_tier.STEWARD = "steward"
        mock_memory.retrieve.return_value = None
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.complete_task("t999", {}) is False

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_complete_task_wrong_agent(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Completing task assigned to different agent returns False."""
        mock_tier.STEWARD = "steward"
        mock_memory.retrieve.return_value = {
            "status": "in_progress",
            "assigned_to": "agent_1",
        }
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.complete_task("t1", {}, agent_id="agent_2") is False

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_complete_task_stash_failure(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Completing task with stash failure returns False."""
        mock_tier.STEWARD = "steward"
        mock_memory.retrieve.return_value = {
            "status": "in_progress",
            "assigned_to": "agent_1",
            "task_type": "review",
        }
        mock_memory.stash.return_value = False
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.complete_task("t1", {"ok": True}, agent_id="agent_1") is False

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_complete_task_no_agent_verification(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Completing without agent_id skips agent check."""
        mock_tier.STEWARD = "steward"
        mock_memory.retrieve.return_value = {
            "status": "in_progress",
            "assigned_to": "agent_1",
            "task_type": "review",
        }
        mock_memory.stash.return_value = True
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.complete_task("t1", {"done": True}) is True

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_register_agent(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Registering an agent stores capabilities."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        result = coord.register_agent("agent_1", capabilities=["review", "audit"])
        assert result is True
        assert "agent_1" in coord._active_agents

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_register_agent_no_capabilities(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Registering an agent without capabilities works."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.register_agent("agent_2") is True

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_heartbeat(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Heartbeat updates active agents timestamp."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        result = coord.heartbeat("agent_1")
        assert result is True
        assert "agent_1" in coord._active_agents

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_active_agents(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Active agents within timeout are returned."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        coord._active_agents = {
            "recent": datetime.now(),
            "old": datetime.now() - timedelta(seconds=600),
        }
        active = coord.get_active_agents(timeout_seconds=300)
        assert "recent" in active
        assert "old" not in active

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_active_agents_empty(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Empty agent list when none registered."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        assert coord.get_active_agents() == []

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_broadcast(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Broadcast sends signal with team_id."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        result = coord.broadcast("alert", {"msg": "hello"})
        assert result is True
        mock_memory.send_signal.assert_called_once()
        call_data = mock_memory.send_signal.call_args[1]["data"]
        assert call_data["team_id"] == "team1"
        assert call_data["msg"] == "hello"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_aggregate_results_empty(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Empty aggregate when no completions."""
        mock_tier.STEWARD = "steward"
        coord = AgentCoordinator(mock_memory, team_id="team1")
        results = coord.aggregate_results()
        assert results["total_completed"] == 0
        assert results["by_agent"] == {}

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_aggregate_results_with_data(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Aggregate with completion signals."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {
                "data": {
                    "task_id": "t1",
                    "agent_id": "agent_1",
                    "task_type": "review",
                    "result_summary": {"issues": 3},
                },
            },
            {
                "data": {
                    "task_id": "t2",
                    "agent_id": "agent_1",
                    "task_type": "review",
                    "result_summary": {"issues": 1},
                },
            },
            {
                "data": {
                    "task_id": "t3",
                    "agent_id": "agent_2",
                    "task_type": "audit",
                },
            },
        ]
        coord = AgentCoordinator(mock_memory, team_id="team1")
        results = coord.aggregate_results()
        assert results["total_completed"] == 3
        assert results["by_agent"]["agent_1"] == 2
        assert results["by_agent"]["agent_2"] == 1
        assert results["by_type"]["review"] == 2
        assert results["by_type"]["audit"] == 1
        assert len(results["summaries"]) == 2

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_aggregate_results_filtered_by_type(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Aggregate filters by task_type."""
        mock_tier.STEWARD = "steward"
        mock_memory.receive_signals.return_value = [
            {"data": {"task_id": "t1", "agent_id": "a", "task_type": "review"}},
            {"data": {"task_id": "t2", "agent_id": "b", "task_type": "audit"}},
        ]
        coord = AgentCoordinator(mock_memory, team_id="team1")
        results = coord.aggregate_results(task_type="review")
        assert results["total_completed"] == 1


# ===================================================================
# Tests: TeamSession
# ===================================================================


class TestTeamSession:
    """Tests for the TeamSession class."""

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_init(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """TeamSession initializes and creates session in Redis."""
        mock_tier.CONTRIBUTOR = "contributor"
        session = TeamSession(mock_memory, session_id="s1", purpose="Test session")
        assert session.session_id == "s1"
        assert session.purpose == "Test session"
        mock_memory.create_session.assert_called_once()

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_add_agent(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Adding an agent joins the session."""
        mock_tier.CONTRIBUTOR = "contributor"
        session = TeamSession(mock_memory, session_id="s1")
        result = session.add_agent("agent_1")
        assert result is True
        mock_memory.join_session.assert_called_once()

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_info(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """get_info returns session data as dict."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.get_session.return_value = {"purpose": "test", "agents": ["a"]}
        session = TeamSession(mock_memory, session_id="s1")
        info = session.get_info()
        assert info is not None
        assert info["purpose"] == "test"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_info_none(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """get_info returns None when session not found."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.get_session.return_value = None
        session = TeamSession(mock_memory, session_id="s1")
        assert session.get_info() is None

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_share(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Sharing data stashes it with session-prefixed key."""
        mock_tier.CONTRIBUTOR = "contributor"
        session = TeamSession(mock_memory, session_id="s1")
        result = session.share("scope", {"files": 10})
        assert result is True
        call_key = mock_memory.stash.call_args[0][0]
        assert call_key == "session:s1:scope"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Getting shared data retrieves from correct key."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.retrieve.return_value = {"files": 10}
        session = TeamSession(mock_memory, session_id="s1")
        data = session.get("scope")
        assert data == {"files": 10}
        call_key = mock_memory.retrieve.call_args[0][0]
        assert call_key == "session:s1:scope"

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_not_found(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Getting missing data returns None."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.retrieve.return_value = None
        session = TeamSession(mock_memory, session_id="s1")
        assert session.get("missing") is None

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_signal(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Sending a signal includes session_id in data."""
        mock_tier.CONTRIBUTOR = "contributor"
        session = TeamSession(mock_memory, session_id="s1")
        result = session.signal("update", {"progress": 50})
        assert result is True
        call_data = mock_memory.send_signal.call_args[1]["data"]
        assert call_data["session_id"] == "s1"
        assert call_data["progress"] == 50

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_signals(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Get signals returns list."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.receive_signals.return_value = [{"type": "update", "data": {}}]
        session = TeamSession(mock_memory, session_id="s1")
        signals = session.get_signals("update")
        assert len(signals) == 1

    @patch("attune.redis_memory.AgentCredentials")
    @patch("attune.redis_memory.AccessTier")
    def test_get_signals_empty(
        self,
        mock_tier: MagicMock,
        mock_creds: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Get signals returns empty list when none found."""
        mock_tier.CONTRIBUTOR = "contributor"
        mock_memory.receive_signals.return_value = None
        session = TeamSession(mock_memory, session_id="s1")
        signals = session.get_signals()
        assert signals == []


# ===================================================================
# Tests: ReleasePreparationWorkflow (SDK-native, v4.2.0)
# ===================================================================


class TestReleasePreparationWorkflowInit:
    """Tests for ReleasePreparationWorkflow initialization (SDK-native)."""

    def test_class_name(self) -> None:
        """Class attribute name is 'release-prep'."""
        assert ReleasePreparationWorkflow.name == "release-prep"

    def test_class_description(self) -> None:
        """Description mentions Agent SDK."""
        assert "Agent SDK" in ReleasePreparationWorkflow.description

    def test_class_stages(self) -> None:
        """SDK-native workflow has single agent-prep stage."""
        assert ReleasePreparationWorkflow.stages == ["agent-prep"]

    def test_default_construction(self) -> None:
        """Default constructor succeeds."""
        wf = ReleasePreparationWorkflow()
        assert wf.name == "release-prep"

    def test_kwargs_passed_to_base(self) -> None:
        """Extra kwargs do not raise."""
        wf = ReleasePreparationWorkflow(enable_post_simplification=False)
        assert wf is not None


class TestReleasePreparationWorkflowReExports:
    """Test backward-compatibility re-exports."""

    def test_release_prep_steps_importable(self) -> None:
        """RELEASE_PREP_STEPS constant is importable."""
        assert isinstance(RELEASE_PREP_STEPS, dict)
        assert len(RELEASE_PREP_STEPS) > 0

    def test_format_release_prep_report_importable(self) -> None:
        """format_release_prep_report is callable."""
        assert callable(format_release_prep_report)

    def test_main_importable(self) -> None:
        """main function is importable."""
        from attune.workflows.release_prep import main

        assert callable(main)


class TestFormatReleasePrepReport:
    """Tests for format_release_prep_report."""

    def test_returns_string(self) -> None:
        """Report formatter returns a string."""
        result_data = {
            "approved": True,
            "recommendation": "Ship it",
            "blockers": [],
        }
        input_data = {
            "health": {"passed": True, "health_score": 100, "failed_checks": []},
            "security": {"vulnerabilities": []},
            "changelog": {"total_commits": 5, "entries": ["SDK migration"]},
        }
        report = format_release_prep_report(result_data, input_data)
        assert isinstance(report, str)
