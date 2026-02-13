"""Pattern Extractor for Continuous Learning

Extracts learnable patterns from collaboration sessions.
Identifies and structures patterns for storage and future application.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.llm.state import CollaborationState

logger = logging.getLogger(__name__)


class PatternCategory(Enum):
    """Categories of extractable patterns."""

    ERROR_RESOLUTION = "error_resolution"  # How errors were resolved
    USER_CORRECTION = "user_correction"  # "Actually, I meant..." patterns
    WORKAROUND = "workaround"  # Framework quirk solutions
    PREFERENCE = "preference"  # Response format preferences
    PROJECT_SPECIFIC = "project_specific"  # Project conventions
    DEBUGGING_TECHNIQUE = "debugging_technique"  # Debugging approaches
    CODE_PATTERN = "code_pattern"  # Code-related patterns


@dataclass
class ExtractedPattern:
    """A pattern extracted from a session."""

    category: PatternCategory
    trigger: str  # What triggers this pattern
    context: str  # Context in which it applies
    resolution: str  # What was done / learned
    confidence: float  # Extraction confidence (0.0-1.0)
    source_session: str  # Session ID
    extracted_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_id(self) -> str:
        """Generate unique pattern ID."""
        content = f"{self.category.value}:{self.trigger}:{self.resolution}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "trigger": self.trigger,
            "context": self.context,
            "resolution": self.resolution,
            "confidence": self.confidence,
            "source_session": self.source_session,
            "extracted_at": self.extracted_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractedPattern:
        """Create from dictionary."""
        return cls(
            category=PatternCategory(data["category"]),
            trigger=data["trigger"],
            context=data["context"],
            resolution=data["resolution"],
            confidence=data.get("confidence", 0.5),
            source_session=data.get("source_session", ""),
            extracted_at=(
                datetime.fromisoformat(data["extracted_at"])
                if "extracted_at" in data
                else datetime.now()
            ),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def format_readable(self) -> str:
        """Format as human-readable text."""
        lines = [
            f"**{self.category.value.replace('_', ' ').title()}**",
            f"- **Trigger**: {self.trigger}",
            f"- **Context**: {self.context}",
            f"- **Resolution**: {self.resolution}",
            f"- **Confidence**: {self.confidence:.0%}",
        ]
        if self.tags:
            lines.append(f"- **Tags**: {', '.join(self.tags)}")
        return "\n".join(lines)


class PatternExtractor:
    """Extracts patterns from collaboration sessions.

    Analyzes session interactions to identify and structure
    patterns that can be learned and applied in future sessions.
    """

    # Correction indicators for user_correction patterns
    CORRECTION_STARTERS = [
        "actually",
        "no,",
        "i meant",
        "let me clarify",
        "to be clear",
        "what i really want",
        "correction:",
    ]

    def __init__(
        self,
        min_confidence: float = 0.3,
        max_patterns_per_session: int = 10,
    ):
        """Initialize the extractor.

        Args:
            min_confidence: Minimum confidence to include pattern
            max_patterns_per_session: Maximum patterns to extract per session
        """
        self._min_confidence = min_confidence
        self._max_patterns = max_patterns_per_session

    def extract_patterns(
        self,
        state: CollaborationState,
        session_id: str = "",
    ) -> list[ExtractedPattern]:
        """Extract all patterns from a session.

        Args:
            state: Collaboration state to analyze
            session_id: Optional session identifier

        Returns:
            List of extracted patterns
        """
        patterns = []

        # Extract user corrections
        patterns.extend(self._extract_corrections(state, session_id))

        # Extract error resolutions
        patterns.extend(self._extract_error_resolutions(state, session_id))

        # Extract workarounds
        patterns.extend(self._extract_workarounds(state, session_id))

        # Extract preferences
        patterns.extend(self._extract_preferences(state, session_id))

        # Extract project-specific patterns
        patterns.extend(self._extract_project_patterns(state, session_id))

        # Filter by confidence and limit
        patterns = [p for p in patterns if p.confidence >= self._min_confidence]
        patterns = sorted(patterns, key=lambda p: p.confidence, reverse=True)
        patterns = patterns[: self._max_patterns]

        logger.info(f"Extracted {len(patterns)} patterns from session")
        return patterns

    def _extract_corrections(
        self,
        state: CollaborationState,
        session_id: str,
    ) -> list[ExtractedPattern]:
        """Extract user correction patterns."""
        patterns = []
        interactions = state.interactions

        for i, interaction in enumerate(interactions):
            if interaction.role != "user":
                continue

            content_lower = interaction.content.lower()

            # Check for correction indicators
            is_correction = any(
                content_lower.startswith(starter) or f" {starter}" in content_lower
                for starter in self.CORRECTION_STARTERS
            )

            if not is_correction:
                continue

            # Get the previous assistant message (what was corrected)
            prev_assistant = None
            for j in range(i - 1, -1, -1):
                if interactions[j].role == "assistant":
                    prev_assistant = interactions[j]
                    break

            # Get the resolution (next assistant message)
            resolution = None
            for j in range(i + 1, len(interactions)):
                if interactions[j].role == "assistant":
                    resolution = interactions[j]
                    break

            if prev_assistant and resolution:
                pattern = ExtractedPattern(
                    category=PatternCategory.USER_CORRECTION,
                    trigger=self._summarize(prev_assistant.content, 100),
                    context=interaction.content,
                    resolution=self._summarize(resolution.content, 150),
                    confidence=0.7,
                    source_session=session_id,
                    tags=["correction", "clarification"],
                )
                patterns.append(pattern)

        return patterns

    def _extract_error_resolutions(
        self,
        state: CollaborationState,
        session_id: str,
    ) -> list[ExtractedPattern]:
        """Extract error resolution patterns."""
        patterns = []
        interactions = state.interactions

        error_patterns = [
            r"error[:\s]",
            r"exception[:\s]",
            r"failed[:\s]",
            r"traceback",
            r"cannot\s",
            r"unable to",
        ]
        error_re = re.compile("|".join(error_patterns), re.IGNORECASE)

        success_patterns = [
            r"that works",
            r"works now",
            r"fixed",
            r"solved",
            r"thank",
            r"perfect",
        ]
        success_re = re.compile("|".join(success_patterns), re.IGNORECASE)

        # Find error mentions and track resolutions
        for i, interaction in enumerate(interactions):
            if interaction.role != "user":
                continue

            if not error_re.search(interaction.content):
                continue

            # Look for successful resolution later
            error_context = interaction.content
            resolution_text = None
            assistant_fix = None

            for j in range(i + 1, len(interactions)):
                other = interactions[j]

                if other.role == "assistant":
                    # Capture the assistant's response to the error
                    if not assistant_fix:
                        assistant_fix = other.content

                elif other.role == "user" and success_re.search(other.content):
                    # Found success confirmation
                    resolution_text = assistant_fix
                    break

            if resolution_text:
                pattern = ExtractedPattern(
                    category=PatternCategory.ERROR_RESOLUTION,
                    trigger=self._extract_error_summary(error_context),
                    context=self._summarize(error_context, 100),
                    resolution=self._summarize(resolution_text, 200),
                    confidence=0.8,
                    source_session=session_id,
                    tags=["error", "debugging", "fix"],
                )
                patterns.append(pattern)

        return patterns

    def _extract_workarounds(
        self,
        state: CollaborationState,
        session_id: str,
    ) -> list[ExtractedPattern]:
        """Extract workaround patterns."""
        patterns = []

        workaround_indicators = [
            r"workaround",
            r"instead",
            r"alternative",
            r"hack",
            r"trick",
            r"work around",
        ]
        workaround_re = re.compile("|".join(workaround_indicators), re.IGNORECASE)

        for interaction in state.interactions:
            if interaction.role != "assistant":
                continue

            if not workaround_re.search(interaction.content):
                continue

            # Extract the workaround description
            content = interaction.content

            pattern = ExtractedPattern(
                category=PatternCategory.WORKAROUND,
                trigger="Framework/library limitation",
                context=self._extract_context_around_keyword(content, workaround_indicators),
                resolution=self._summarize(content, 200),
                confidence=0.6,
                source_session=session_id,
                tags=["workaround", "hack"],
            )
            patterns.append(pattern)

        return patterns

    def _extract_preferences(
        self,
        state: CollaborationState,
        session_id: str,
    ) -> list[ExtractedPattern]:
        """Extract user preference patterns."""
        patterns = []

        preference_indicators = [
            (r"i prefer\s+(\w+(?:\s+\w+){0,5})", "preference"),
            (r"i like\s+(\w+(?:\s+\w+){0,5})", "like"),
            (r"i don't like\s+(\w+(?:\s+\w+){0,5})", "dislike"),
            (r"please always\s+(\w+(?:\s+\w+){0,5})", "always"),
            (r"please don't\s+(\w+(?:\s+\w+){0,5})", "never"),
            (r"i always\s+(\w+(?:\s+\w+){0,5})", "habit"),
        ]

        for interaction in state.interactions:
            if interaction.role != "user":
                continue

            content_lower = interaction.content.lower()

            for pattern_str, pref_type in preference_indicators:
                matches = re.findall(pattern_str, content_lower)
                for match in matches:
                    pattern = ExtractedPattern(
                        category=PatternCategory.PREFERENCE,
                        trigger=pref_type,
                        context=f"User expressed: {match}",
                        resolution=self._summarize(interaction.content, 100),
                        confidence=0.5,
                        source_session=session_id,
                        tags=["preference", pref_type],
                    )
                    patterns.append(pattern)

        return patterns

    def _extract_project_patterns(
        self,
        state: CollaborationState,
        session_id: str,
    ) -> list[ExtractedPattern]:
        """Extract project-specific patterns."""
        patterns = []

        # Look for conventions, file structures, naming patterns
        convention_indicators = [
            r"in this project",
            r"we always",
            r"our convention",
            r"the pattern here",
            r"this codebase",
        ]
        convention_re = re.compile("|".join(convention_indicators), re.IGNORECASE)

        for interaction in state.interactions:
            if not convention_re.search(interaction.content):
                continue

            pattern = ExtractedPattern(
                category=PatternCategory.PROJECT_SPECIFIC,
                trigger="Project convention",
                context=self._extract_context_around_keyword(
                    interaction.content, convention_indicators
                ),
                resolution=self._summarize(interaction.content, 150),
                confidence=0.6,
                source_session=session_id,
                tags=["project", "convention"],
            )
            patterns.append(pattern)

        return patterns

    def _summarize(self, text: str, max_length: int) -> str:
        """Summarize text to max length."""
        text = text.strip()
        if len(text) <= max_length:
            return text

        # Try to cut at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")

        cut_point = max(last_period, last_newline)
        if cut_point > max_length // 2:
            return truncated[: cut_point + 1].strip()

        return truncated.strip() + "..."

    def _extract_error_summary(self, error_text: str) -> str:
        """Extract a summary of the error."""
        # Look for common error patterns
        error_patterns = [
            r"(Error|Exception):\s*([^\n]+)",
            r"(cannot|unable to)\s+([^\n.]+)",
            r"(failed to)\s+([^\n.]+)",
        ]

        for pattern in error_patterns:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                return match.group(0)[:100]

        # Fall back to first line
        first_line = error_text.split("\n")[0]
        return self._summarize(first_line, 100)

    def _extract_context_around_keyword(
        self,
        text: str,
        keywords: list[str],
    ) -> str:
        """Extract context around matching keywords."""
        text_lower = text.lower()

        for keyword in keywords:
            # Clean keyword for search
            search_term = keyword.replace(r"\s+", " ").replace("\\", "")
            match = re.search(search_term, text_lower, re.IGNORECASE)

            if match:
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)

                context = text[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."

                return context

        return self._summarize(text, 150)

    def categorize_pattern(
        self,
        trigger: str,
        content: str,
    ) -> PatternCategory:
        """Categorize a pattern based on content.

        Args:
            trigger: The trigger text
            content: The pattern content

        Returns:
            Appropriate PatternCategory
        """
        content_lower = content.lower()
        trigger_lower = trigger.lower()

        if any(word in content_lower for word in ["error", "exception", "failed", "fix", "bug"]):
            return PatternCategory.ERROR_RESOLUTION

        if any(word in trigger_lower for word in ["actually", "correction", "meant", "clarify"]):
            return PatternCategory.USER_CORRECTION

        if any(word in content_lower for word in ["workaround", "instead", "alternative", "hack"]):
            return PatternCategory.WORKAROUND

        if any(word in content_lower for word in ["prefer", "like", "always", "never", "style"]):
            return PatternCategory.PREFERENCE

        if any(
            word in content_lower for word in ["project", "codebase", "convention", "this repo"]
        ):
            return PatternCategory.PROJECT_SPECIFIC

        return PatternCategory.CODE_PATTERN
