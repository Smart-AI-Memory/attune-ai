"""Context Manager for Empathy Framework

Orchestrates context compaction, state preservation, and restoration.
Integrates with the hook system to handle compaction events automatically.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from attune_llm.context.compaction import (
    CompactionStateManager,
    CompactState,
    PatternSummary,
    SBARHandoff,
)

if TYPE_CHECKING:
    from attune_llm.state import CollaborationState, UserPattern

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages context compaction and restoration for the Empathy Framework.

    This class coordinates:
    - Converting CollaborationState to CompactState for preservation
    - Restoring state after context window resets
    - Generating restoration prompts
    - Handling SBAR handoffs for work continuity
    """

    def __init__(
        self,
        storage_dir: str | Path = ".attune/compact_states",
        token_threshold: int = 50,  # Percentage at which to suggest compaction
        auto_save: bool = True,
    ):
        """Initialize the ContextManager.

        Args:
            storage_dir: Directory for state persistence
            token_threshold: Token usage percentage to trigger compaction suggestions
            auto_save: Whether to auto-save state on compaction
        """
        self._state_manager = CompactionStateManager(storage_dir=storage_dir)
        self._token_threshold = token_threshold
        self._auto_save = auto_save
        self._current_session_id: str = ""
        self._current_phase: str = ""
        self._completed_phases: list[str] = []
        self._pending_handoff: SBARHandoff | None = None

    @property
    def session_id(self) -> str:
        """Get current session ID."""
        return self._current_session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        """Set current session ID."""
        self._current_session_id = value

    @property
    def current_phase(self) -> str:
        """Get current work phase."""
        return self._current_phase

    @current_phase.setter
    def current_phase(self, value: str) -> None:
        """Set current work phase."""
        self._current_phase = value

    def complete_phase(self, phase: str) -> None:
        """Mark a phase as completed.

        Args:
            phase: Name of the completed phase
        """
        if phase not in self._completed_phases:
            self._completed_phases.append(phase)
        logger.debug(f"Completed phase: {phase}")

    def set_handoff(
        self,
        situation: str,
        background: str,
        assessment: str,
        recommendation: str,
        priority: str = "normal",
        **metadata: Any,
    ) -> SBARHandoff:
        """Set a pending handoff for work continuity.

        Uses SBAR format for clear communication:
        - Situation: What's happening now
        - Background: Relevant context
        - Assessment: Current understanding
        - Recommendation: Suggested next action

        Args:
            situation: Current situation description
            background: Relevant background information
            assessment: Current assessment
            recommendation: Recommended next action
            priority: Priority level (low, normal, high, critical)
            **metadata: Additional metadata

        Returns:
            The created SBARHandoff
        """
        self._pending_handoff = SBARHandoff(
            situation=situation,
            background=background,
            assessment=assessment,
            recommendation=recommendation,
            priority=priority,
            metadata=metadata,
        )
        return self._pending_handoff

    def clear_handoff(self) -> None:
        """Clear the pending handoff after it's been addressed."""
        self._pending_handoff = None

    def extract_compact_state(
        self,
        collaboration_state: CollaborationState,
    ) -> CompactState:
        """Extract CompactState from full CollaborationState.

        Converts the rich collaboration state into a compact form
        suitable for preservation through context resets.

        Args:
            collaboration_state: Full collaboration state

        Returns:
            Compact state for preservation
        """
        # Convert patterns to summaries
        pattern_summaries = [
            self._pattern_to_summary(p)
            for p in collaboration_state.detected_patterns[:10]  # Top 10
        ]

        # Extract key preferences (limit to essentials)
        key_preferences = self._extract_key_preferences(collaboration_state.preferences)

        return CompactState(
            user_id=collaboration_state.user_id,
            trust_level=collaboration_state.trust_level,
            empathy_level=collaboration_state.current_level,
            detected_patterns=pattern_summaries,
            session_id=self._current_session_id,
            current_phase=self._current_phase,
            completed_phases=list(self._completed_phases),
            pending_handoff=self._pending_handoff,
            interaction_count=len(collaboration_state.interactions),
            successful_actions=collaboration_state.successful_actions,
            failed_actions=collaboration_state.failed_actions,
            preferences=key_preferences,
        )

    def _pattern_to_summary(self, pattern: UserPattern) -> PatternSummary:
        """Convert UserPattern to PatternSummary.

        Args:
            pattern: Full pattern object

        Returns:
            Compact pattern summary
        """
        return PatternSummary(
            pattern_type=pattern.pattern_type.value,
            trigger=pattern.trigger,
            action=pattern.action,
            confidence=pattern.confidence,
            occurrences=pattern.occurrences,
        )

    def _extract_key_preferences(
        self,
        preferences: dict[str, Any],
        max_items: int = 10,
    ) -> dict[str, Any]:
        """Extract key preferences for compaction.

        Filters and limits preferences to essential items.

        Args:
            preferences: Full preferences dict
            max_items: Maximum items to include

        Returns:
            Filtered preferences dict
        """
        # Priority keys to always include if present
        priority_keys = {
            "response_style",
            "code_style",
            "verbosity",
            "confirmation_level",
            "tool_usage",
            "language",
            "timezone",
        }

        result: dict[str, Any] = {}

        # Add priority keys first
        for key in priority_keys:
            if key in preferences:
                result[key] = preferences[key]
                if len(result) >= max_items:
                    return result

        # Add remaining keys up to limit
        for key, value in preferences.items():
            if key not in result:
                # Skip complex nested structures
                if isinstance(value, str | int | float | bool):
                    result[key] = value
                elif isinstance(value, list) and len(value) <= 5:
                    result[key] = value

            if len(result) >= max_items:
                break

        return result

    def save_for_compaction(
        self,
        collaboration_state: CollaborationState,
    ) -> Path:
        """Save state for upcoming compaction.

        Called before context compaction to preserve state.

        Args:
            collaboration_state: Current collaboration state

        Returns:
            Path to saved state file
        """
        compact_state = self.extract_compact_state(collaboration_state)
        return self._state_manager.save_state(compact_state)

    def restore_state(self, user_id: str) -> CompactState | None:
        """Restore the most recent state for a user.

        Args:
            user_id: User identifier

        Returns:
            Most recent CompactState or None
        """
        state = self._state_manager.load_latest_state(user_id)

        if state:
            # Restore session tracking
            self._current_session_id = state.session_id
            self._current_phase = state.current_phase
            self._completed_phases = list(state.completed_phases)
            self._pending_handoff = state.pending_handoff

            logger.info(f"Restored state for user {user_id}")

        return state

    def restore_by_session(self, session_id: str) -> CompactState | None:
        """Restore state for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            CompactState for session or None
        """
        state = self._state_manager.load_state_by_session(session_id)

        if state:
            self._current_session_id = state.session_id
            self._current_phase = state.current_phase
            self._completed_phases = list(state.completed_phases)
            self._pending_handoff = state.pending_handoff

            logger.info(f"Restored state for session {session_id}")

        return state

    def generate_restoration_prompt(self, user_id: str) -> str | None:
        """Generate a restoration prompt for session continuity.

        Loads the most recent state and formats it as a prompt
        that can be injected at session start.

        Args:
            user_id: User identifier

        Returns:
            Formatted restoration prompt or None if no state
        """
        state = self.restore_state(user_id)

        if not state:
            return None

        return state.format_restoration_prompt()

    def should_suggest_compaction(
        self,
        token_usage_percent: float,
        message_count: int | None = None,
    ) -> bool:
        """Determine if compaction should be suggested.

        Args:
            token_usage_percent: Current token usage as percentage (0-100)
            message_count: Optional message count for additional heuristic

        Returns:
            True if compaction should be suggested
        """
        # Primary check: token usage
        if token_usage_percent >= self._token_threshold:
            return True

        # Secondary check: message count (if provided)
        if message_count and message_count >= 50:
            return True

        return False

    def get_compaction_message(
        self,
        token_usage_percent: float,
    ) -> str:
        """Generate a compaction suggestion message.

        Args:
            token_usage_percent: Current token usage percentage

        Returns:
            Formatted suggestion message
        """
        return (
            f"Context usage at {token_usage_percent:.0f}%. "
            "Consider running `/compact` to preserve state and free context space. "
            "Your collaboration state, trust level, and detected patterns will be preserved."
        )

    def apply_state_to_collaboration(
        self,
        compact_state: CompactState,
        collaboration_state: CollaborationState,
    ) -> None:
        """Apply restored CompactState to CollaborationState.

        Updates a CollaborationState with values from a restored CompactState.

        Args:
            compact_state: State to restore from
            collaboration_state: State to update
        """
        # Restore trust level
        collaboration_state.trust_level = compact_state.trust_level

        # Restore empathy level
        collaboration_state.current_level = compact_state.empathy_level

        # Restore counters
        collaboration_state.successful_actions = compact_state.successful_actions
        collaboration_state.failed_actions = compact_state.failed_actions

        # Restore preferences
        collaboration_state.preferences.update(compact_state.preferences)

        # Note: Patterns and interactions are not restored from compact state
        # as the full state would be needed for those

        logger.info(
            f"Applied compact state to collaboration: "
            f"trust={compact_state.trust_level:.2f}, "
            f"level={compact_state.empathy_level}"
        )

    def get_state_summary(self, user_id: str) -> dict[str, Any] | None:
        """Get a summary of saved states for a user.

        Args:
            user_id: User identifier

        Returns:
            Summary dict or None if no states
        """
        states = self._state_manager.get_all_states(user_id)

        if not states:
            return None

        latest = states[0]

        return {
            "user_id": user_id,
            "states_count": len(states),
            "latest_saved": latest.saved_at,
            "latest_trust_level": latest.trust_level,
            "latest_empathy_level": latest.empathy_level,
            "latest_session_id": latest.session_id,
            "patterns_count": len(latest.detected_patterns),
            "has_pending_handoff": latest.pending_handoff is not None,
        }

    def clear_states(self, user_id: str) -> int:
        """Clear all saved states for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of states cleared
        """
        return self._state_manager.clear_user_states(user_id)
