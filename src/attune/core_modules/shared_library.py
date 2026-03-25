"""Shared Library Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides async context manager support and shared pattern library methods
for multi-agent collaboration (Level 5 Systems Empathy).

Expected attributes on the host class:
    user_id (str): User identifier
    shared_library (PatternLibrary | None): Shared pattern library
    persistence_enabled (bool): Whether persistence is enabled

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..pattern_library import PatternLibrary


class SharedLibraryMixin:
    """Mixin providing shared pattern library and async context manager support."""

    # Expected attributes (set by EmpathyOS.__init__)
    user_id: str
    shared_library: PatternLibrary | None
    persistence_enabled: bool

    async def __aenter__(self) -> SharedLibraryMixin:
        """Enter async context manager.

        Enables usage: async with EmpathyOS(...) as empathy:

        Returns:
            self: The EmpathyOS instance

        """
        # Initialize any async resources here if needed
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager

        Performs cleanup when exiting the context:
        - Saves patterns if persistence is enabled
        - Closes any open connections
        - Logs final collaboration state

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to propagate exceptions (standard behavior)

        """
        await self._cleanup()
        return False  # Don't suppress exceptions

    async def _cleanup(self):
        """Cleanup resources on context exit

        **Extension Point**: Override to add custom cleanup logic
        (e.g., save state to database, close connections, send metrics)
        """
        # Future: Save patterns to disk
        # Future: Send final metrics
        # Future: Close async connections

    def contribute_pattern(self, pattern) -> None:
        """Contribute a discovered pattern to the shared library.

        Enables Level 5 Systems Empathy: patterns discovered by this agent
        become available to all other agents sharing the same library.

        Args:
            pattern: Pattern object to contribute

        Raises:
            RuntimeError: If no shared library is configured

        Example:
            >>> from attune import Pattern, PatternLibrary
            >>> library = PatternLibrary()
            >>> agent = EmpathyOS(user_id="code_reviewer", shared_library=library)
            >>> pattern = Pattern(
            ...     id="pat_001",
            ...     agent_id="code_reviewer",
            ...     pattern_type="best_practice",
            ...     name="Test pattern",
            ...     description="A discovered pattern",
            ... )
            >>> agent.contribute_pattern(pattern)

        """
        if self.shared_library is None:
            raise RuntimeError(
                "No shared library configured. Pass shared_library to __init__ "
                "to enable multi-agent pattern sharing.",
            )
        self.shared_library.contribute_pattern(self.user_id, pattern)

    def query_patterns(self, context: dict, **kwargs) -> list:
        """Query the shared library for patterns relevant to the current context.

        Enables agents to benefit from patterns discovered by other agents
        in the distributed memory network.

        Args:
            context: Dictionary describing the current context
            **kwargs: Additional arguments passed to PatternLibrary.query_patterns()
                     (e.g., pattern_type, min_confidence, limit)

        Returns:
            List of PatternMatch objects sorted by relevance

        Raises:
            RuntimeError: If no shared library is configured

        Example:
            >>> matches = agent.query_patterns(
            ...     context={"language": "python", "task": "code_review"},
            ...     min_confidence=0.7
            ... )
            >>> for match in matches:
            ...     print(f"{match.pattern.name}: {match.relevance_score:.0%}")

        """
        if self.shared_library is None:
            raise RuntimeError(
                "No shared library configured. Pass shared_library to __init__ "
                "to enable multi-agent pattern sharing.",
            )
        return self.shared_library.query_patterns(self.user_id, context, **kwargs)

    def has_shared_library(self) -> bool:
        """Check if this agent has a shared pattern library configured."""
        return self.shared_library is not None
