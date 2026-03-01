"""Pattern promotion mixin for UnifiedMemory.

Handles promotion of patterns from short-term to long-term memory.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..long_term import Classification
    from ..types import AgentCredentials

logger = structlog.get_logger(__name__)


class PatternPromotionMixin:
    """Mixin providing pattern promotion capabilities for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    _short_term: Any  # MemoryBackend | None
    _long_term: Any  # SecureMemDocsIntegration | None

    # Needs access to methods from other mixins
    @property
    def credentials(self) -> "AgentCredentials":
        """Get credentials - provided by ShortTermOperationsMixin."""

    def get_staged_patterns(self) -> list[dict]:
        """Get staged patterns - provided by ShortTermOperationsMixin."""

    def persist_pattern(
        self,
        content: str,
        pattern_type: str,
        classification: "Classification | str | None" = None,
        auto_classify: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Persist pattern - provided by LongTermOperationsMixin."""

    # =========================================================================
    # PATTERN PROMOTION (SHORT-TERM → LONG-TERM)
    # =========================================================================

    def promote_pattern(
        self,
        staged_pattern_id: str,
        classification: "Classification | str | None" = None,
        auto_classify: bool = True,
    ) -> dict[str, Any] | None:
        """Promote a staged pattern from short-term to long-term memory.

        Args:
            staged_pattern_id: ID of staged pattern to promote
            classification: Override classification (or auto-detect)
            auto_classify: Auto-detect classification from content

        Returns:
            Long-term storage result, or None if failed

        """
        if not self._short_term or not self._long_term:
            logger.error("memory_backends_unavailable")
            return None

        # Retrieve staged pattern
        staged_patterns = self.get_staged_patterns()
        staged = next(
            (p for p in staged_patterns if p.get("pattern_id") == staged_pattern_id),
            None,
        )

        if not staged:
            logger.warning("staged_pattern_not_found", pattern_id=staged_pattern_id)
            return None

        # Persist to long-term storage
        # Content is stored in context dict by stage_pattern
        context = staged.get("context", {})
        content = context.get("content", "") or staged.get("description", "")
        result = self.persist_pattern(
            content=content,
            pattern_type=staged.get("pattern_type", "general"),
            classification=classification,
            auto_classify=auto_classify,
            metadata=context,
        )

        if result:
            # Remove from staging (use promote_pattern which handles deletion)
            try:
                self._short_term.promote_pattern(staged_pattern_id, self.credentials)
            except PermissionError:
                # If we can't promote (delete from staging), just log it
                logger.warning("could_not_remove_from_staging", pattern_id=staged_pattern_id)
            logger.info(
                "pattern_promoted",
                staged_id=staged_pattern_id,
                long_term_id=result.get("pattern_id"),
            )

        return result
