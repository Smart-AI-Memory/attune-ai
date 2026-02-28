"""Memory Interface Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides unified memory property and convenience methods for
short-term (stash/retrieve) and long-term (persist/recall) storage.

Expected attributes on the host class:
    user_id (str): User identifier
    credentials (AgentCredentials): Agent credentials with access tier
    _unified_memory (UnifiedMemory | None): Lazily initialized memory

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..memory import Classification, UnifiedMemory
    from ..memory.types import AgentCredentials


class MemoryInterfaceMixin:
    """Mixin providing unified memory access for EmpathyOS."""

    # Expected attributes (set by EmpathyOS.__init__)
    user_id: str
    credentials: AgentCredentials
    _unified_memory: UnifiedMemory | None

    @property
    def memory(self) -> UnifiedMemory:
        """Unified memory interface for both short-term and long-term storage.

        Lazily initializes on first access with environment auto-detection.

        Usage:
            empathy = EmpathyOS(user_id="agent_1")

            # Store working data (short-term)
            empathy.memory.stash("analysis", {"results": [...]})

            # Persist pattern (long-term)
            result = empathy.memory.persist_pattern(
                content="Algorithm for X",
                pattern_type="algorithm",
            )

            # Retrieve pattern
            pattern = empathy.memory.recall_pattern(result["pattern_id"])
        """
        from ..memory import UnifiedMemory

        if self._unified_memory is None:
            self._unified_memory = UnifiedMemory(
                user_id=self.user_id,
                access_tier=self.credentials.tier,
            )
        return self._unified_memory

    def persist_pattern(
        self,
        content: str,
        pattern_type: str,
        classification: Classification | str | None = None,
        auto_classify: bool = True,
    ) -> dict | None:
        """Store a pattern in long-term memory with security controls.

        This is a convenience method that delegates to memory.persist_pattern().

        Args:
            content: Pattern content
            pattern_type: Type (algorithm, protocol, config, etc.)
            classification: Security classification (or auto-detect)
            auto_classify: Auto-detect classification from content

        Returns:
            Storage result with pattern_id and classification

        Example:
            >>> empathy = EmpathyOS(user_id="dev@company.com")
            >>> result = empathy.persist_pattern(
            ...     content="Our proprietary algorithm for...",
            ...     pattern_type="algorithm",
            ... )
            >>> print(result["classification"])  # "INTERNAL"

        """
        return self.memory.persist_pattern(
            content=content,
            pattern_type=pattern_type,
            classification=classification,
            auto_classify=auto_classify,
        )

    def recall_pattern(self, pattern_id: str) -> dict | None:
        """Retrieve a pattern from long-term memory.

        This is a convenience method that delegates to memory.recall_pattern().

        Args:
            pattern_id: ID of pattern to retrieve

        Returns:
            Pattern data with content and metadata

        Example:
            >>> pattern = empathy.recall_pattern("pat_123")
            >>> print(pattern["content"])

        """
        return self.memory.recall_pattern(pattern_id)

    def stash(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Store data in short-term memory with TTL.

        This is a convenience method that delegates to memory.stash().

        Args:
            key: Storage key
            value: Data to store
            ttl_seconds: Time-to-live (default 1 hour)

        Returns:
            True if stored successfully

        """
        return self.memory.stash(key, value, ttl_seconds)

    def retrieve(self, key: str) -> Any:
        """Retrieve data from short-term memory.

        This is a convenience method that delegates to memory.retrieve().

        Args:
            key: Storage key

        Returns:
            Stored data or None

        """
        return self.memory.retrieve(key)
