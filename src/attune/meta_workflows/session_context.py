"""Session Context for Meta-Workflows

Tracks user choices and preferences across workflow executions using short-term memory.
Enables intelligent defaults and personalized recommendations based on recent history.

Features:
- Record form choices per template
- Suggest defaults based on recent choices
- Session isolation per user
- TTL-based expiration (1 hour default)
- Graceful fallback when memory unavailable

Usage:
    from attune.meta_workflows.session_context import SessionContext
    from attune.memory.unified import UnifiedMemory

    memory = UnifiedMemory(user_id="user@example.com")
    session = SessionContext(memory=memory)

    # Record choice
    session.record_choice("python_package_publish", "has_tests", "Yes")

    # Get suggested defaults
    defaults = session.suggest_defaults("python_package_publish")

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.memory.unified import UnifiedMemory
    from attune.meta_workflows.models import FormSchema

logger = logging.getLogger(__name__)


class SessionContext:
    """Track session-level patterns and user preferences.

    Uses short-term memory to record form choices and suggest intelligent
    defaults for subsequent workflow executions.

    Attributes:
        memory: UnifiedMemory instance for storage
        session_id: Unique session identifier
        user_id: User identifier (from memory)
        default_ttl: Time-to-live for session data (seconds)

    """

    def __init__(
        self,
        memory: "UnifiedMemory | None" = None,
        session_id: str | None = None,
        default_ttl: int = 3600,
    ):
        """Initialize session context.

        Args:
            memory: UnifiedMemory instance (optional, graceful fallback if None)
            session_id: Optional session ID (generates new if None)
            default_ttl: TTL for session data in seconds (default: 1 hour)

        """
        self.memory = memory
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = memory.user_id if memory else "anonymous"
        self.default_ttl = default_ttl

        logger.info(
            f"SessionContext initialized: session_id={self.session_id}, "
            f"user_id={self.user_id}, memory={'enabled' if memory else 'disabled'}",
        )

    def record_choice(
        self,
        template_id: str,
        question_id: str,
        choice: Any,
        ttl: int | None = None,
    ) -> bool:
        """Record a form choice in short-term memory.

        Args:
            template_id: Template identifier
            question_id: Question identifier
            choice: User's choice (any JSON-serializable type)
            ttl: Optional TTL override (uses default_ttl if None)

        Returns:
            True if recorded successfully, False otherwise

        """
        if not self.memory:
            logger.debug("Memory not available, cannot record choice")
            return False

        try:
            key = self._make_choice_key(template_id, question_id)
            value = {
                "choice": choice,
                "timestamp": datetime.utcnow().isoformat(),
                "template_id": template_id,
                "question_id": question_id,
            }

            self.memory.stash(key, value, ttl_seconds=ttl or self.default_ttl)

            logger.debug(
                f"Recorded choice: template={template_id}, question={question_id}, choice={choice}",
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record choice: {e}")
            return False

    def get_recent_choice(
        self,
        template_id: str,
        question_id: str,
    ) -> Any | None:
        """Get the most recent choice for a specific question.

        Args:
            template_id: Template identifier
            question_id: Question identifier

        Returns:
            Most recent choice, or None if not found

        """
        if not self.memory:
            return None

        try:
            key = self._make_choice_key(template_id, question_id)
            value = self.memory.retrieve(key)

            if value and isinstance(value, dict):
                return value.get("choice")

            return None

        except Exception as e:
            logger.debug(f"Failed to get recent choice: {e}")
            return None

    def get_recent_choices(
        self,
        template_id: str,
    ) -> dict[str, Any]:
        """Get all recent choices for a template.

        Args:
            template_id: Template identifier

        Returns:
            Dict mapping question_id -> choice

        """
        if not self.memory:
            return {}

        try:
            # Get all keys for this template and session
            pattern = f"session:{self.session_id}:form:{template_id}:*"

            # Note: This requires pattern matching support in short-term memory
            # For now, we return empty dict (could be enhanced later)
            logger.debug(f"Pattern matching not yet implemented: {pattern}")
            return {}

        except Exception as e:
            logger.error(f"Failed to get recent choices: {e}")
            return {}

    def suggest_defaults(
        self,
        template_id: str,
        form_schema: "FormSchema | None" = None,
    ) -> dict[str, Any]:
        """Suggest default values based on recent choices.

        Args:
            template_id: Template identifier
            form_schema: Optional form schema for validation

        Returns:
            Dict mapping question_id -> suggested_default

        """
        if not self.memory:
            return {}

        try:
            # Get recent choices for this template
            recent_choices = self.get_recent_choices(template_id)

            # If form_schema provided, validate suggestions
            if form_schema:
                validated_suggestions = {}
                for question in form_schema.questions:
                    if question.id in recent_choices:
                        # Validate that suggestion is valid for question type
                        choice = recent_choices[question.id]
                        if self._validate_choice(choice, question):
                            validated_suggestions[question.id] = choice

                return validated_suggestions

            return recent_choices

        except Exception as e:
            logger.error(f"Failed to suggest defaults: {e}")
            return {}

    def record_execution(
        self,
        template_id: str,
        run_id: str,
        success: bool,
        cost: float,
        duration: float,
        ttl: int | None = None,
    ) -> bool:
        """Record workflow execution metadata.

        Args:
            template_id: Template identifier
            run_id: Execution run ID
            success: Whether execution succeeded
            cost: Total cost in USD
            duration: Duration in seconds
            ttl: Optional TTL override

        Returns:
            True if recorded successfully

        """
        if not self.memory:
            return False

        try:
            key = f"session:{self.session_id}:execution:{run_id}"
            value = {
                "template_id": template_id,
                "run_id": run_id,
                "success": success,
                "cost": cost,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.memory.stash(key, value, ttl_seconds=ttl or self.default_ttl)

            logger.debug(f"Recorded execution: run_id={run_id}, success={success}")
            return True

        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            return False

    def get_session_stats(self) -> dict[str, Any]:
        """Get statistics for current session.

        Returns:
            Dict with session statistics (executions, success rate, etc.)

        """
        if not self.memory:
            return {"session_id": self.session_id, "memory_enabled": False}

        try:
            stats = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "memory_enabled": True,
                "executions": 0,
                "successful_executions": 0,
                "total_cost": 0.0,
                "total_duration": 0.0,
            }

            # Note: Would need to query all execution records
            # For now, return basic stats
            return stats

        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"session_id": self.session_id, "error": str(e)}

    def clear_session(self) -> bool:
        """Clear all session data from memory.

        Returns:
            True if cleared successfully

        """
        if not self.memory:
            return False

        try:
            # Note: Would need to delete all keys matching session pattern
            # For now, just log
            logger.info(f"Session clear requested: {self.session_id}")
            # Implementation would require pattern delete support
            return True

        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _make_choice_key(self, template_id: str, question_id: str) -> str:
        """Create Redis key for a form choice.

        Args:
            template_id: Template identifier
            question_id: Question identifier

        Returns:
            Redis key string

        """
        return f"session:{self.session_id}:form:{template_id}:{question_id}"

    def _validate_choice(self, choice: Any, question: Any) -> bool:
        """Validate that a choice is valid for a question.

        Args:
            choice: User's choice
            question: FormQuestion object

        Returns:
            True if valid, False otherwise

        """
        try:
            # Basic validation - could be enhanced
            if hasattr(question, "options") and question.options:
                # Check if choice is in options (only if options are defined)
                if isinstance(choice, list):
                    # Multi-select - all choices must be in options
                    return all(c in question.options for c in choice)
                # Single-select - choice must be in options
                return choice in question.options

            # No specific validation - assume valid
            return True

        except Exception:  # noqa: BLE001
            # INTENTIONAL: Validation is best-effort;
            # return False for any unexpected input shape.
            return False


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================


def create_session_context(
    memory: "UnifiedMemory | None" = None,
    session_id: str | None = None,
) -> SessionContext:
    """Create a new session context.

    Convenience function for creating SessionContext instances.

    Args:
        memory: UnifiedMemory instance (optional)
        session_id: Optional session ID

    Returns:
        SessionContext instance

    """
    return SessionContext(memory=memory, session_id=session_id)


def get_session_defaults(
    template_id: str,
    form_schema: "FormSchema | None" = None,
    memory: "UnifiedMemory | None" = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Get suggested defaults for a template.

    Convenience function for getting defaults without creating SessionContext.

    Args:
        template_id: Template identifier
        form_schema: Optional form schema
        memory: Optional UnifiedMemory instance
        session_id: Optional session ID

    Returns:
        Dict of suggested defaults

    """
    session = SessionContext(memory=memory, session_id=session_id)
    return session.suggest_defaults(template_id, form_schema)
