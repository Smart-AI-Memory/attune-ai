"""Session Evaluator for Continuous Learning

Evaluates sessions to determine if they contain learnable patterns.
Identifies high-value sessions worth analyzing for pattern extraction.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.llm.state import CollaborationState

logger = logging.getLogger(__name__)


class SessionQuality(Enum):
    """Quality rating for a session."""

    EXCELLENT = "excellent"  # High learning value
    GOOD = "good"  # Worth extracting patterns
    AVERAGE = "average"  # Some value
    POOR = "poor"  # Limited learning value
    SKIP = "skip"  # Don't process


@dataclass
class SessionMetrics:
    """Metrics computed for a session."""

    interaction_count: int = 0
    user_corrections: int = 0
    successful_resolutions: int = 0
    trust_delta: float = 0.0
    empathy_level_avg: float = 0.0
    error_mentions: int = 0
    workaround_mentions: int = 0
    preference_signals: int = 0
    session_duration_minutes: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "interaction_count": self.interaction_count,
            "user_corrections": self.user_corrections,
            "successful_resolutions": self.successful_resolutions,
            "trust_delta": self.trust_delta,
            "empathy_level_avg": self.empathy_level_avg,
            "error_mentions": self.error_mentions,
            "workaround_mentions": self.workaround_mentions,
            "preference_signals": self.preference_signals,
            "session_duration_minutes": self.session_duration_minutes,
        }


@dataclass
class EvaluationResult:
    """Result of session evaluation."""

    quality: SessionQuality
    score: float  # 0.0 to 1.0
    metrics: SessionMetrics
    learnable_topics: list[str] = field(default_factory=list)
    recommended_extraction: bool = False
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "quality": self.quality.value,
            "score": self.score,
            "metrics": self.metrics.to_dict(),
            "learnable_topics": self.learnable_topics,
            "recommended_extraction": self.recommended_extraction,
            "reasoning": self.reasoning,
        }


class SessionEvaluator:
    """Evaluates sessions for learning potential.

    Analyzes collaboration sessions to determine if they contain
    patterns worth extracting for continuous learning.
    """

    # Patterns indicating user corrections
    CORRECTION_PATTERNS = [
        r"actually[,\s]",
        r"i meant",
        r"no[,\s]+i",
        r"that's not what i",
        r"let me clarify",
        r"to be clear",
        r"what i really",
        r"i should have said",
        r"correction:",
    ]

    # Patterns indicating errors/debugging
    ERROR_PATTERNS = [
        r"error",
        r"exception",
        r"failed",
        r"doesn't work",
        r"not working",
        r"broken",
        r"bug",
        r"issue",
        r"problem",
        r"crash",
    ]

    # Patterns indicating workarounds
    WORKAROUND_PATTERNS = [
        r"workaround",
        r"instead[,\s]",
        r"alternative",
        r"hack",
        r"trick",
        r"bypass",
        r"work around",
        r"quick fix",
    ]

    # Patterns indicating preferences
    PREFERENCE_PATTERNS = [
        r"i prefer",
        r"i like",
        r"i don't like",
        r"i always",
        r"i never",
        r"my style",
        r"usually i",
        r"please always",
        r"please don't",
    ]

    # Patterns indicating successful resolution
    SUCCESS_PATTERNS = [
        r"that works",
        r"perfect",
        r"thanks",
        r"great",
        r"solved",
        r"fixed",
        r"working now",
        r"exactly what i",
    ]

    def __init__(
        self,
        min_interactions: int = 3,
        min_score_for_extraction: float = 0.4,
    ):
        """Initialize the evaluator.

        Args:
            min_interactions: Minimum interactions for evaluation
            min_score_for_extraction: Minimum score to recommend extraction

        """
        self._min_interactions = min_interactions
        self._min_score_for_extraction = min_score_for_extraction

        # Compile patterns
        self._correction_re = self._compile_patterns(self.CORRECTION_PATTERNS)
        self._error_re = self._compile_patterns(self.ERROR_PATTERNS)
        self._workaround_re = self._compile_patterns(self.WORKAROUND_PATTERNS)
        self._preference_re = self._compile_patterns(self.PREFERENCE_PATTERNS)
        self._success_re = self._compile_patterns(self.SUCCESS_PATTERNS)

    def _compile_patterns(self, patterns: list[str]) -> re.Pattern:
        """Compile patterns into a single regex."""
        combined = "|".join(f"({p})" for p in patterns)
        return re.compile(combined, re.IGNORECASE)

    def evaluate(
        self,
        state: CollaborationState,
    ) -> EvaluationResult:
        """Evaluate a collaboration session.

        Args:
            state: The collaboration state to evaluate

        Returns:
            EvaluationResult with quality rating and metrics

        """
        # Compute metrics
        metrics = self._compute_metrics(state)

        # Determine learnable topics
        topics = self._identify_topics(state, metrics)

        # Calculate score
        score = self._calculate_score(metrics, len(topics))

        # Determine quality
        quality = self._score_to_quality(score)

        # Build reasoning
        reasoning = self._build_reasoning(metrics, topics, score)

        return EvaluationResult(
            quality=quality,
            score=score,
            metrics=metrics,
            learnable_topics=topics,
            recommended_extraction=score >= self._min_score_for_extraction,
            reasoning=reasoning,
        )

    def _compute_metrics(self, state: CollaborationState) -> SessionMetrics:
        """Compute session metrics."""
        metrics = SessionMetrics()

        metrics.interaction_count = len(state.interactions)

        if metrics.interaction_count == 0:
            return metrics

        # Calculate duration
        if state.interactions:
            first = state.interactions[0].timestamp
            last = state.interactions[-1].timestamp
            duration = (last - first).total_seconds() / 60.0
            metrics.session_duration_minutes = duration

        # Calculate trust delta
        if state.trust_trajectory:
            initial = state.trust_trajectory[0] if state.trust_trajectory else 0.5
            final = state.trust_level
            metrics.trust_delta = final - initial

        # Calculate average empathy level
        if state.level_history:
            metrics.empathy_level_avg = sum(state.level_history) / len(state.level_history)
        else:
            metrics.empathy_level_avg = state.current_level

        # Analyze user messages
        for interaction in state.interactions:
            if interaction.role != "user":
                continue

            content_lower = interaction.content.lower()

            # Count corrections
            if self._correction_re.search(content_lower):
                metrics.user_corrections += 1

            # Count error mentions
            if self._error_re.search(content_lower):
                metrics.error_mentions += 1

            # Count workaround mentions
            if self._workaround_re.search(content_lower):
                metrics.workaround_mentions += 1

            # Count preference signals
            if self._preference_re.search(content_lower):
                metrics.preference_signals += 1

            # Count successful resolutions
            if self._success_re.search(content_lower):
                metrics.successful_resolutions += 1

        return metrics

    def _identify_topics(
        self,
        state: CollaborationState,
        metrics: SessionMetrics,
    ) -> list[str]:
        """Identify learnable topics from the session."""
        topics = []

        if metrics.user_corrections > 0:
            topics.append("user_corrections")

        if metrics.error_mentions > 0 and metrics.successful_resolutions > 0:
            topics.append("error_resolution")

        if metrics.workaround_mentions > 0:
            topics.append("workarounds")

        if metrics.preference_signals > 0:
            topics.append("preferences")

        # Check for project-specific patterns
        if self._has_project_specific_content(state):
            topics.append("project_specific")

        return topics

    def _has_project_specific_content(self, state: CollaborationState) -> bool:
        """Check if session contains project-specific content."""
        # Look for file paths, function names, etc.
        project_indicators = [
            r"\.(py|js|ts|tsx|jsx|go|rs|java|cpp|c|h)\b",  # File extensions
            r"def\s+\w+",  # Python functions
            r"function\s+\w+",  # JS functions
            r"class\s+\w+",  # Class definitions
            r"import\s+",  # Imports
            r"from\s+\w+\s+import",  # Python imports
        ]

        project_re = re.compile("|".join(project_indicators), re.IGNORECASE)

        for interaction in state.interactions:
            if project_re.search(interaction.content):
                return True

        return False

    def _calculate_score(
        self,
        metrics: SessionMetrics,
        topic_count: int,
    ) -> float:
        """Calculate overall learning score."""
        score = 0.0

        # Base score from interaction count
        if metrics.interaction_count >= self._min_interactions:
            score += 0.1

        # Corrections are highly valuable
        if metrics.user_corrections > 0:
            score += min(metrics.user_corrections * 0.15, 0.3)

        # Error resolutions are valuable
        if metrics.error_mentions > 0 and metrics.successful_resolutions > 0:
            resolution_rate = metrics.successful_resolutions / max(metrics.error_mentions, 1)
            score += resolution_rate * 0.2

        # Workarounds are valuable
        if metrics.workaround_mentions > 0:
            score += min(metrics.workaround_mentions * 0.1, 0.2)

        # Preferences help personalization
        if metrics.preference_signals > 0:
            score += min(metrics.preference_signals * 0.05, 0.1)

        # Topic diversity bonus
        score += topic_count * 0.05

        # Trust increase indicates good interactions
        if metrics.trust_delta > 0:
            score += min(metrics.trust_delta * 0.2, 0.1)

        # Penalize very short sessions
        if metrics.interaction_count < self._min_interactions:
            score *= 0.5

        return min(score, 1.0)

    def _score_to_quality(self, score: float) -> SessionQuality:
        """Convert score to quality rating."""
        if score >= 0.7:
            return SessionQuality.EXCELLENT
        if score >= 0.5:
            return SessionQuality.GOOD
        if score >= 0.3:
            return SessionQuality.AVERAGE
        if score >= 0.1:
            return SessionQuality.POOR
        return SessionQuality.SKIP

    def _build_reasoning(
        self,
        metrics: SessionMetrics,
        topics: list[str],
        score: float,
    ) -> str:
        """Build human-readable reasoning."""
        parts = []

        if metrics.user_corrections > 0:
            parts.append(f"{metrics.user_corrections} user correction(s) found")

        if metrics.successful_resolutions > 0:
            parts.append(f"{metrics.successful_resolutions} successful resolution(s)")

        if metrics.workaround_mentions > 0:
            parts.append(f"{metrics.workaround_mentions} workaround(s) discussed")

        if metrics.preference_signals > 0:
            parts.append(f"{metrics.preference_signals} preference signal(s)")

        if topics:
            parts.append(f"Learnable topics: {', '.join(topics)}")

        if not parts:
            parts.append("Limited learning signals detected")

        return "; ".join(parts) + f". Score: {score:.2f}"

    def should_extract_patterns(
        self,
        state: CollaborationState,
    ) -> bool:
        """Quick check if patterns should be extracted.

        Args:
            state: Collaboration state to check

        Returns:
            True if extraction is recommended

        """
        result = self.evaluate(state)
        return result.recommended_extraction

    def get_extraction_priority(
        self,
        state: CollaborationState,
    ) -> int:
        """Get extraction priority (higher = more important).

        Args:
            state: Collaboration state to evaluate

        Returns:
            Priority from 0-100

        """
        result = self.evaluate(state)
        return int(result.score * 100)
