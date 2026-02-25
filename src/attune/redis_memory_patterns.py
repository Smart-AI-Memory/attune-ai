"""Redis Memory Pattern Staging for Attune AI

Pattern staging workflow methods for RedisShortTermMemory:
- stage_pattern: Stage a pattern for validation
- get_staged_pattern: Retrieve a staged pattern
- list_staged_patterns: List all staged patterns
- promote_pattern: Promote staged pattern to library
- reject_pattern: Reject a staged pattern

Per EMPATHY_PHILOSOPHY.md: Patterns must be staged before
being promoted to the active library.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json

from .memory.types import AgentCredentials, StagedPattern, TTLStrategy


class PatternStagingMixin:
    """Mixin providing pattern staging operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, _delete, _keys, and PREFIX_STAGED.
    """

    def stage_pattern(
        self,
        pattern: StagedPattern,
        credentials: AgentCredentials,
    ) -> bool:
        """Stage a pattern for validation

        Per EMPATHY_PHILOSOPHY.md: Patterns must be staged before
        being promoted to the active library.

        Args:
            pattern: Pattern to stage
            credentials: Must be CONTRIBUTOR or higher

        Returns:
            True if staged successfully

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot stage patterns. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        key = f"{self.PREFIX_STAGED}{pattern.pattern_id}"
        return self._set(
            key,
            json.dumps(pattern.to_dict()),
            TTLStrategy.STAGED_PATTERNS.value,
        )

    def get_staged_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Retrieve a staged pattern

        Args:
            pattern_id: Pattern ID
            credentials: Any tier can read

        Returns:
            StagedPattern or None

        """
        key = f"{self.PREFIX_STAGED}{pattern_id}"
        raw = self._get(key)

        if raw is None:
            return None

        return StagedPattern.from_dict(json.loads(raw))

    def list_staged_patterns(
        self,
        credentials: AgentCredentials,
    ) -> list[StagedPattern]:
        """List all staged patterns awaiting validation

        Args:
            credentials: Any tier can read

        Returns:
            List of staged patterns

        """
        pattern = f"{self.PREFIX_STAGED}*"
        keys = self._keys(pattern)
        patterns = []

        for key in keys:
            raw = self._get(key)
            if raw:
                patterns.append(StagedPattern.from_dict(json.loads(raw)))

        return patterns

    def promote_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Promote staged pattern (remove from staging for library add)

        Args:
            pattern_id: Pattern to promote
            credentials: Must be VALIDATOR or higher

        Returns:
            The promoted pattern (for adding to PatternLibrary)

        """
        if not credentials.can_validate():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot promote patterns. "
                "Requires VALIDATOR tier or higher.",
            )

        pattern = self.get_staged_pattern(pattern_id, credentials)
        if pattern:
            key = f"{self.PREFIX_STAGED}{pattern_id}"
            self._delete(key)
        return pattern

    def reject_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
        reason: str = "",
    ) -> bool:
        """Reject a staged pattern

        Args:
            pattern_id: Pattern to reject
            credentials: Must be VALIDATOR or higher
            reason: Rejection reason (for audit)

        Returns:
            True if rejected

        """
        if not credentials.can_validate():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot reject patterns. "
                "Requires VALIDATOR tier or higher.",
            )

        key = f"{self.PREFIX_STAGED}{pattern_id}"
        return self._delete(key)
