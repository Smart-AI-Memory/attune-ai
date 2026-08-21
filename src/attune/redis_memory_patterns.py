"""Deprecated — use attune_redis for pattern promotion.

Superseded by attune_redis.AMSMemoryBackend (the Redis Agent Memory Server integration). Retained — attune is aligning on Redis + Anthropic Claude, so there is no planned removal. Migration path: docs/migration/redis-plugin-migration.md

Legacy pattern staging mixins kept for backward
compatibility. New code should use
``attune_redis.memory.AMSMemoryBackend.promote()``.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import warnings

warnings.warn(
    "attune.redis_memory_patterns is deprecated. "
    "Use attune_redis.memory.AMSMemoryBackend.promote() instead.",
    DeprecationWarning,
    stacklevel=2,
)

import json  # noqa: E402
from typing import TYPE_CHECKING  # noqa: E402

from .memory.types import (  # noqa: E402
    AgentCredentials,
    StagedPattern,
    TTLStrategy,
    parse_stored_record,
)


class PatternStagingMixin:
    """Mixin providing pattern staging operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, _delete, _keys, and PREFIX_STAGED.
    """

    PREFIX_STAGED: str

    if TYPE_CHECKING:

        def _get(self, key: str) -> str | None: ...
        def _set(self, key: str, value: str, ttl: int | None = None) -> bool: ...
        def _delete(self, key: str) -> bool: ...
        def _keys(self, pattern: str) -> list[str]: ...

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
        return bool(
            self._set(
                key,
                json.dumps(pattern.to_dict()),
                TTLStrategy.STAGED_PATTERNS.value,
            )
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

        # Deserialize-here / subscript-there (library-review I-4): a
        # legacy or hand-edited value that parses to a LIST makes
        # from_dict raise TypeError from inside the call, past a caller
        # whose except tuple lists only JSONDecodeError. parse_stored_record
        # collapses all three failure modes to None.
        return parse_stored_record(StagedPattern, raw, key=key)

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
            if not raw:
                continue
            # One unreadable key must not block the listing that backs
            # every promotion (library-review I-4, P15: degrade, never
            # block).
            staged = parse_stored_record(StagedPattern, raw, key=key)
            if staged is not None:
                patterns.append(staged)

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
