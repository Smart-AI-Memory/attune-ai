"""Pattern staging workflow - stage, validate, promote/reject.

This module provides the pattern staging lifecycle:
- Stage: Store patterns for validation (CONTRIBUTOR+)
- Get/List: Retrieve staged patterns (any tier)
- Promote: Move pattern to active library (VALIDATOR+)
- Reject: Remove pattern from staging (VALIDATOR+)

Key Prefix: PREFIX_STAGED = "empathy:staged:"

Classes:
    PatternStaging: Pattern staging lifecycle operations

Example:
    >>> from attune.memory.short_term.patterns import PatternStaging
    >>> from attune.memory.types import AgentCredentials, AccessTier, StagedPattern
    >>> staging = PatternStaging(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> pattern = StagedPattern(pattern_id="p1", name="Test", ...)
    >>> staging.stage_pattern(pattern, creds)
    >>> staged = staging.list_staged_patterns(creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
    StagedPattern,
    TTLStrategy,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class PatternStaging:
    """Pattern staging lifecycle operations.

    Implements the pattern validation workflow per EMPATHY_PHILOSOPHY.md:
    - Patterns must be staged before being promoted to active library
    - CONTRIBUTOR tier can stage patterns
    - VALIDATOR tier can promote or reject patterns

    The class is designed to be composed with BaseOperations
    for dependency injection.

    Attributes:
        PREFIX_STAGED: Key prefix for staged patterns namespace

    Example:
        >>> staging = PatternStaging(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> staging.stage_pattern(pattern, creds)
        True
        >>> staging.list_staged_patterns(creds)
        [StagedPattern(...)]

    """

    PREFIX_STAGED = "empathy:staged:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize pattern staging operations.

        Args:
            base: BaseOperations instance for storage access

        """
        self._base = base

    def stage_pattern(
        self,
        pattern: StagedPattern,
        credentials: AgentCredentials,
    ) -> bool:
        """Stage a pattern for validation.

        Per EMPATHY_PHILOSOPHY.md: Patterns must be staged before
        being promoted to the active library.

        Args:
            pattern: Pattern to stage
            credentials: Must be CONTRIBUTOR or higher

        Returns:
            True if staged successfully

        Raises:
            TypeError: If pattern is not StagedPattern
            PermissionError: If credentials lack staging access

        Example:
            >>> pattern = StagedPattern(pattern_id="p1", name="Test", ...)
            >>> staging.stage_pattern(pattern, creds)
            True

        """
        # Pattern 5: Type validation
        if not isinstance(pattern, StagedPattern):
            raise TypeError(f"pattern must be StagedPattern, got {type(pattern).__name__}")

        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot stage patterns. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        key = f"{self.PREFIX_STAGED}{pattern.pattern_id}"
        return self._base._set(
            key,
            json.dumps(pattern.to_dict()),
            TTLStrategy.STAGED_PATTERNS.value,
        )

    def get_staged_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Retrieve a staged pattern.

        Args:
            pattern_id: Pattern ID
            credentials: Any tier can read

        Returns:
            StagedPattern or None if not found

        Raises:
            ValueError: If pattern_id is empty

        Example:
            >>> pattern = staging.get_staged_pattern("p1", creds)
            >>> if pattern:
            ...     print(f"Found: {pattern.name}")

        """
        # Pattern 1: String ID validation
        if not pattern_id or not pattern_id.strip():
            raise ValueError(f"pattern_id cannot be empty. Got: {pattern_id!r}")

        key = f"{self.PREFIX_STAGED}{pattern_id}"
        raw = self._base._get(key)

        if raw is None:
            return None

        return StagedPattern.from_dict(json.loads(raw))

    def list_staged_patterns(
        self,
        credentials: AgentCredentials,
    ) -> list[StagedPattern]:
        """List all staged patterns awaiting validation.

        Args:
            credentials: Any tier can read

        Returns:
            List of staged patterns

        Example:
            >>> patterns = staging.list_staged_patterns(creds)
            >>> for p in patterns:
            ...     print(f"{p.pattern_id}: {p.name}")

        """
        pattern = f"{self.PREFIX_STAGED}*"
        keys = self._base._keys(pattern)
        patterns = []

        for raw in self._base._mget(keys):
            if raw:
                patterns.append(StagedPattern.from_dict(json.loads(raw)))

        return patterns

    def promote_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Promote staged pattern (remove from staging for library add).

        Args:
            pattern_id: Pattern to promote
            credentials: Must be VALIDATOR or higher

        Returns:
            The promoted pattern (for adding to PatternLibrary)

        Raises:
            PermissionError: If credentials lack validation access

        Example:
            >>> pattern = staging.promote_pattern("p1", validator_creds)
            >>> if pattern:
            ...     pattern_library.add(pattern)

        """
        if not credentials.can_validate():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot promote patterns. "
                "Requires VALIDATOR tier or higher.",
            )

        pattern = self.get_staged_pattern(pattern_id, credentials)
        if pattern:
            key = f"{self.PREFIX_STAGED}{pattern_id}"
            self._base._delete(key)
        return pattern

    def reject_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
        reason: str = "",
    ) -> bool:
        """Reject a staged pattern.

        Args:
            pattern_id: Pattern to reject
            credentials: Must be VALIDATOR or higher
            reason: Rejection reason (for audit)

        Returns:
            True if rejected

        Raises:
            PermissionError: If credentials lack validation access

        Example:
            >>> staging.reject_pattern("p1", validator_creds, "Not applicable")
            True

        """
        if not credentials.can_validate():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot reject patterns. "
                "Requires VALIDATOR tier or higher.",
            )

        key = f"{self.PREFIX_STAGED}{pattern_id}"
        deleted = self._base._delete(key)

        if deleted and reason:
            logger.info(
                "pattern_rejected",
                pattern_id=pattern_id,
                agent_id=credentials.agent_id,
                reason=reason,
            )

        return deleted

    def count_staged(self) -> int:
        """Count the number of staged patterns.

        Returns:
            Number of staged patterns

        Example:
            >>> count = staging.count_staged()
            >>> print(f"{count} patterns awaiting validation")

        """
        pattern = f"{self.PREFIX_STAGED}*"
        return len(self._base._keys(pattern))
