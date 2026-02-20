"""Conflict Resolution for Multi-Agent Pattern Libraries

Provides conflict resolution primitives for multi-agent systems sharing
pattern libraries.

When multiple agents discover conflicting patterns, the ConflictResolver
determines which pattern should take precedence based on:
1. Team priorities (configured preferences)
2. Context match (relevance to current situation)
3. Confidence scores (historical success rate)
4. Recency (newer patterns may reflect updated practices)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..pattern_library import Pattern


class ResolutionStrategy(Enum):
    """Strategy for resolving pattern conflicts"""

    HIGHEST_CONFIDENCE = "highest_confidence"  # Pick pattern with highest confidence
    MOST_RECENT = "most_recent"  # Pick most recently discovered pattern
    BEST_CONTEXT_MATCH = "best_context_match"  # Pick best match for current context
    TEAM_PRIORITY = "team_priority"  # Use team-configured priorities
    WEIGHTED_SCORE = "weighted_score"  # Combine multiple factors


@dataclass
class ResolutionResult:
    """Result of conflict resolution between patterns"""

    winning_pattern: Pattern
    losing_patterns: list[Pattern]
    strategy_used: ResolutionStrategy
    confidence: float  # How confident in this resolution (0-1)
    reasoning: str  # Explanation of why this pattern won
    factors: dict[str, float] = field(default_factory=dict)  # Score breakdown


@dataclass
class TeamPriorities:
    """Team-configured priorities for conflict resolution"""

    # Priority weights (should sum to 1.0)
    readability_weight: float = 0.3
    performance_weight: float = 0.2
    security_weight: float = 0.3
    maintainability_weight: float = 0.2

    # Pattern type preferences (higher = preferred)
    type_preferences: dict[str, float] = field(
        default_factory=lambda: {
            "security": 1.0,
            "best_practice": 0.8,
            "performance": 0.7,
            "style": 0.5,
            "warning": 0.6,
        },
    )

    # Tag preferences (tags that should be prioritized)
    preferred_tags: list[str] = field(default_factory=list)


class ConflictResolver:
    """Resolves conflicts between patterns from different agents.

    When multiple agents contribute patterns that address the same issue
    but recommend different approaches, the ConflictResolver determines
    which pattern should take precedence.

    Example:
        >>> resolver = ConflictResolver()
        >>>
        >>> # Two agents have different recommendations
        >>> review_pattern = Pattern(
        ...     id="use_list_comprehension",
        ...     agent_id="code_reviewer",
        ...     pattern_type="performance",
        ...     name="Use list comprehension",
        ...     description="Use list comprehension for better performance",
        ...     confidence=0.85
        ... )
        >>>
        >>> style_pattern = Pattern(
        ...     id="use_explicit_loop",
        ...     agent_id="style_agent",
        ...     pattern_type="style",
        ...     name="Use explicit loop",
        ...     description="Use explicit loop for better readability",
        ...     confidence=0.80
        ... )
        >>>
        >>> resolution = resolver.resolve_patterns(
        ...     patterns=[review_pattern, style_pattern],
        ...     context={"team_priority": "readability", "code_complexity": "high"}
        ... )
        >>> print(f"Winner: {resolution.winning_pattern.name}")

    """

    def __init__(
        self,
        default_strategy: ResolutionStrategy = ResolutionStrategy.WEIGHTED_SCORE,
        team_priorities: TeamPriorities | None = None,
    ):
        """Initialize the ConflictResolver.

        Args:
            default_strategy: Strategy to use when not specified
            team_priorities: Team-configured priorities for resolution

        """
        self.default_strategy = default_strategy
        self.team_priorities = team_priorities or TeamPriorities()
        self.resolution_history: list[ResolutionResult] = []

    def resolve_patterns(
        self,
        patterns: list[Pattern],
        context: dict[str, Any] | None = None,
        strategy: ResolutionStrategy | None = None,
    ) -> ResolutionResult:
        """Resolve conflict between multiple patterns.

        Args:
            patterns: List of conflicting patterns (minimum 2)
            context: Current context for resolution decision
            strategy: Resolution strategy (uses default if not specified)

        Returns:
            ResolutionResult with winning pattern and reasoning

        Raises:
            ValueError: If fewer than 2 patterns provided

        """
        if len(patterns) < 2:
            raise ValueError("Need at least 2 patterns to resolve conflict")

        context = context or {}
        strategy = strategy or self.default_strategy

        # Calculate scores for each pattern
        scored_patterns = [
            (pattern, self._calculate_pattern_score(pattern, context, strategy))
            for pattern in patterns
        ]

        # Sort by score (highest first)
        scored_patterns.sort(key=lambda x: x[1]["total"], reverse=True)

        winner, winner_scores = scored_patterns[0]
        losers = [p for p, _ in scored_patterns[1:]]

        # Generate reasoning
        reasoning = self._generate_reasoning(winner, losers, winner_scores, context, strategy)

        result = ResolutionResult(
            winning_pattern=winner,
            losing_patterns=losers,
            strategy_used=strategy,
            confidence=winner_scores["total"],
            reasoning=reasoning,
            factors=winner_scores,
        )

        # Track history for learning
        self.resolution_history.append(result)

        return result

    def _calculate_pattern_score(
        self,
        pattern: Pattern,
        context: dict[str, Any],
        strategy: ResolutionStrategy,
    ) -> dict[str, float]:
        """Calculate score for a pattern based on strategy"""
        scores: dict[str, float] = {}

        # Factor 1: Confidence score (0-1)
        scores["confidence"] = pattern.confidence

        # Factor 2: Success rate (0-1)
        scores["success_rate"] = pattern.success_rate if pattern.usage_count > 0 else 0.5

        # Factor 3: Recency (0-1, more recent = higher)
        age_days = (datetime.now() - pattern.discovered_at).days
        scores["recency"] = max(0, 1 - (age_days / 365))  # Decay over 1 year

        # Factor 4: Context match (0-1)
        scores["context_match"] = self._calculate_context_match(pattern, context)

        # Factor 5: Team priority alignment (0-1)
        scores["team_alignment"] = self._calculate_team_alignment(pattern, context)

        # Calculate total based on strategy
        if strategy == ResolutionStrategy.HIGHEST_CONFIDENCE:
            scores["total"] = scores["confidence"]
        elif strategy == ResolutionStrategy.MOST_RECENT:
            scores["total"] = scores["recency"]
        elif strategy == ResolutionStrategy.BEST_CONTEXT_MATCH:
            scores["total"] = scores["context_match"]
        elif strategy == ResolutionStrategy.TEAM_PRIORITY:
            scores["total"] = scores["team_alignment"]
        else:  # WEIGHTED_SCORE
            scores["total"] = (
                scores["confidence"] * 0.25
                + scores["success_rate"] * 0.25
                + scores["recency"] * 0.15
                + scores["context_match"] * 0.20
                + scores["team_alignment"] * 0.15
            )

        return scores

    def _calculate_context_match(
        self,
        pattern: Pattern,
        context: dict[str, Any],
    ) -> float:
        """Calculate how well a pattern matches the current context"""
        if not context or not pattern.context:
            return 0.5  # Neutral if no context available

        # Check key overlaps
        pattern_keys = set(pattern.context.keys())
        context_keys = set(context.keys())
        common_keys = pattern_keys & context_keys

        if not common_keys:
            return 0.3  # Low match if no common keys

        # Count matching values
        matches = sum(1 for key in common_keys if pattern.context.get(key) == context.get(key))

        match_ratio = matches / len(common_keys) if common_keys else 0

        # Check tag overlap
        context_tags = set(context.get("tags", []))
        pattern_tags = set(pattern.tags)
        tag_overlap = len(context_tags & pattern_tags)
        tag_bonus = min(tag_overlap * 0.1, 0.2)  # Up to 0.2 bonus for tags

        return min(match_ratio * 0.8 + tag_bonus + 0.1, 1.0)

    def _calculate_team_alignment(
        self,
        pattern: Pattern,
        context: dict[str, Any],
    ) -> float:
        """Calculate how well a pattern aligns with team priorities"""
        score = 0.5  # Start neutral

        # Check team priority in context
        team_priority = context.get("team_priority", "").lower()

        # Map priorities to pattern characteristics
        priority_boosts = {
            "readability": ["style", "best_practice", "documentation"],
            "performance": ["performance", "optimization"],
            "security": ["security", "vulnerability", "warning"],
            "maintainability": ["best_practice", "refactoring", "style"],
        }

        if team_priority in priority_boosts:
            boosted_types = priority_boosts[team_priority]
            if pattern.pattern_type.lower() in boosted_types:
                score += 0.3

            # Check if any tags match
            for tag in pattern.tags:
                if tag.lower() in boosted_types:
                    score += 0.1
                    break

        # Apply type preference from team config
        type_pref = self.team_priorities.type_preferences.get(pattern.pattern_type.lower(), 0.5)
        score = (score + type_pref) / 2

        # Bonus for preferred tags
        for tag in pattern.tags:
            if tag in self.team_priorities.preferred_tags:
                score += 0.1
                break

        return min(score, 1.0)

    def _generate_reasoning(
        self,
        winner: Pattern,
        losers: list[Pattern],
        scores: dict[str, float],
        context: dict[str, Any],
        strategy: ResolutionStrategy,
    ) -> str:
        """Generate human-readable reasoning for the resolution"""
        reasons = []

        # Strategy-specific reasoning
        if strategy == ResolutionStrategy.HIGHEST_CONFIDENCE:
            reasons.append(
                f"Selected '{winner.name}' with highest confidence ({winner.confidence:.0%})",
            )
        elif strategy == ResolutionStrategy.MOST_RECENT:
            age = (datetime.now() - winner.discovered_at).days
            reasons.append(f"Selected '{winner.name}' as most recent (discovered {age} days ago)")
        elif strategy == ResolutionStrategy.BEST_CONTEXT_MATCH:
            reasons.append(
                f"Selected '{winner.name}' as best match for current context "
                f"(match score: {scores['context_match']:.0%})",
            )
        elif strategy == ResolutionStrategy.TEAM_PRIORITY:
            team_priority = context.get("team_priority", "balanced")
            reasons.append(f"Selected '{winner.name}' based on team priority: {team_priority}")
        else:  # WEIGHTED_SCORE
            top_factors = sorted(
                [(k, v) for k, v in scores.items() if k != "total"],
                key=lambda x: x[1],
                reverse=True,
            )[:2]
            factor_desc = ", ".join(f"{k}: {v:.0%}" for k, v in top_factors)
            reasons.append(
                f"Selected '{winner.name}' based on weighted scoring (top factors: {factor_desc})",
            )

        # Add comparison to losers
        if losers:
            loser_names = [p.name for p in losers[:2]]
            reasons.append(f"Preferred over: {', '.join(loser_names)}")

        return ". ".join(reasons)

    def get_resolution_stats(self) -> dict[str, Any]:
        """Get statistics about resolution history"""
        if not self.resolution_history:
            return {
                "total_resolutions": 0,
                "strategies_used": {},
                "average_confidence": 0.0,
            }

        strategies: dict[str, int] = {}
        confidences: list[float] = []

        for result in self.resolution_history:
            strategy = result.strategy_used.value
            strategies[strategy] = strategies.get(strategy, 0) + 1
            confidences.append(result.confidence)

        most_used = max(strategies.keys(), key=lambda k: strategies[k]) if strategies else None

        return {
            "total_resolutions": len(self.resolution_history),
            "strategies_used": strategies,
            "average_confidence": sum(confidences) / len(confidences),
            "most_used_strategy": most_used,
        }

    def clear_history(self):
        """Clear resolution history"""
        self.resolution_history = []
