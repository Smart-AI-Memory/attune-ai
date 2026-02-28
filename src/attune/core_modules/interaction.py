"""Interaction Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides state management, synchronous interaction, and trust tracking.

Expected attributes on the host class:
    user_id (str): User identifier
    target_level (int): Target empathy level
    logger (logging.Logger): Logger instance
    current_empathy_level (int): Current empathy level
    collaboration_state (CollaborationState): Collaboration state

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core import CollaborationState, InteractionResponse


class InteractionMixin:
    """Mixin providing state management, interaction, and trust tracking."""

    # Expected attributes (set by EmpathyOS.__init__)
    user_id: str
    target_level: int
    logger: Any  # logging.Logger
    current_empathy_level: int
    collaboration_state: CollaborationState

    def get_collaboration_state(self) -> dict:
        """Get current collaboration state"""
        return {
            "trust_level": self.collaboration_state.trust_level,
            "total_interactions": self.collaboration_state.total_interactions,
            "success_rate": (
                self.collaboration_state.successful_interventions
                / self.collaboration_state.total_interactions
                if self.collaboration_state.total_interactions > 0
                else 0
            ),
            "current_empathy_level": self.current_empathy_level,
            "target_empathy_level": self.target_level,
        }

    def reset_collaboration_state(self):
        """Reset collaboration state (new session)"""
        from ..core import CollaborationState

        self.collaboration_state = CollaborationState()

    def interact(
        self,
        user_id: str,
        user_input: str,
        context: dict | None = None,
    ) -> InteractionResponse:
        """Process a user interaction and return a response.

        This is a synchronous convenience method for simple interactions.
        For full empathy level control, use the level_X_* async methods.

        Args:
            user_id: User identifier
            user_input: The user's input text
            context: Optional context dictionary

        Returns:
            InteractionResponse with level, response, confidence, and optional predictions

        Example:
            >>> empathy = EmpathyOS(user_id="dev_123")
            >>> response = empathy.interact(
            ...     user_id="dev_123",
            ...     user_input="How do I optimize this query?",
            ...     context={"domain": "database"}
            ... )
            >>> print(f"[L{response.level}] {response.response}")

        """
        from ..core import InteractionResponse

        context = context or {}

        # Determine appropriate empathy level based on trust and context
        current_trust = self.collaboration_state.trust_level
        level = self._determine_interaction_level(current_trust, context)

        # Generate response based on level
        response_text = self._generate_response(user_input, context, level)

        # For Level 4+, generate predictions
        predictions = None
        if level >= 4:
            predictions = self._generate_predictions(user_input, context)

        # Calculate confidence based on context completeness and trust
        confidence = self._calculate_confidence(context, current_trust)

        # Update interaction tracking
        self.collaboration_state.total_interactions += 1
        self.current_empathy_level = level

        return InteractionResponse(
            level=level,
            response=response_text,
            confidence=confidence,
            predictions=predictions,
        )

    def record_success(self, success: bool) -> None:
        """Record the outcome of an interaction for trust tracking.

        Call this after receiving user feedback on whether an interaction
        was helpful. Updates the collaboration state's trust level.

        Args:
            success: True if the interaction was helpful, False otherwise

        Example:
            >>> response = empathy.interact(...)
            >>> # After getting user feedback
            >>> feedback = input("Was this helpful? (y/n): ")
            >>> empathy.record_success(success=(feedback.lower() == 'y'))
            >>> print(f"Trust level: {empathy.collaboration_state.trust_level:.0%}")

        """
        outcome = "success" if success else "failure"
        self.collaboration_state.update_trust(outcome)

        self.logger.debug(
            f"Recorded interaction outcome: {outcome}",
            extra={
                "user_id": self.user_id,
                "success": success,
                "new_trust_level": self.collaboration_state.trust_level,
            },
        )

    def _determine_interaction_level(self, trust: float, context: dict) -> int:
        """Determine appropriate empathy level for interaction.

        Args:
            trust: Current trust level (0.0 to 1.0)
            context: Interaction context

        Returns:
            Empathy level (1-5)

        """
        # Start conservative, increase with trust
        if trust < 0.3:
            return 1  # Reactive only
        if trust < 0.5:
            return 2  # Guided
        if trust < 0.7:
            return min(3, self.target_level)  # Proactive
        if trust < 0.85:
            return min(4, self.target_level)  # Anticipatory
        return min(5, self.target_level)  # Systems

    def _generate_response(self, user_input: str, context: dict, level: int) -> str:
        """Generate response based on empathy level.

        **Extension Point**: Override this method to implement domain-specific
        response generation (e.g., using LLMs, templates, or rule engines).

        Args:
            user_input: User's input text
            context: Interaction context
            level: Empathy level to use

        Returns:
            Response text

        """
        # Default implementation - override for real logic
        level_descriptions = {
            1: "Reactive response",
            2: "Guided response with clarification",
            3: "Proactive response anticipating needs",
            4: "Anticipatory response predicting future needs",
            5: "Systems-level response addressing root patterns",
        }
        return (
            f"[Level {level}] {level_descriptions.get(level, 'Response')}: "
            f"Processing '{user_input}'"
        )

    def _generate_predictions(self, user_input: str, context: dict) -> list[str]:
        """Generate predictions for Level 4+ interactions.

        **Extension Point**: Override to implement domain-specific prediction logic.

        Args:
            user_input: User's input text
            context: Interaction context

        Returns:
            List of prediction strings

        """
        # Default implementation - override for real predictions
        return ["Potential follow-up: Related topics may include..."]

    def _calculate_confidence(self, context: dict, trust: float) -> float:
        """Calculate confidence score for response.

        Args:
            context: Interaction context
            trust: Current trust level

        Returns:
            Confidence score (0.0 to 1.0)

        """
        # Base confidence on context completeness and trust
        context_score = min(1.0, len(context) * 0.1) if context else 0.5
        return (context_score + trust) / 2
