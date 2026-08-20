"""Long-term memory operations mixin for UnifiedMemory.

Provides pattern persistence, retrieval, search, and caching.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import heapq
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..long_term import Classification

logger = structlog.get_logger(__name__)


class LongTermOperationsMixin:
    """Mixin providing long-term memory operations for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    user_id: str
    _long_term: Any  # SecureMemDocsIntegration | None
    _pattern_cache: dict[str, dict[str, Any]]
    _pattern_cache_max_size: int

    # =========================================================================
    # LONG-TERM MEMORY OPERATIONS
    # =========================================================================

    def persist_pattern(
        self,
        content: str,
        pattern_type: str,
        classification: "Classification | str | None" = None,
        auto_classify: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Store a pattern in long-term memory with security controls.

        Args:
            content: Pattern content
            pattern_type: Type of pattern (algorithm, protocol, etc.)
            classification: Security classification (PUBLIC/INTERNAL/SENSITIVE)
            auto_classify: Auto-detect classification from content
            metadata: Additional metadata to store

        Returns:
            Storage result with pattern_id and classification, or None if failed

        """
        from ..long_term import Classification

        if not self._long_term:
            logger.error("long_term_memory_unavailable")
            return None

        try:
            # Convert string classification to enum if needed
            explicit_class = None
            if classification is not None:
                if isinstance(classification, str):
                    explicit_class = Classification[classification.upper()]
                else:
                    explicit_class = classification

            result = self._long_term.store_pattern(
                content=content,
                pattern_type=pattern_type,
                user_id=self.user_id,
                explicit_classification=explicit_class,
                auto_classify=auto_classify,
                custom_metadata=metadata,
            )
            logger.info(
                "pattern_persisted",
                pattern_id=result.get("pattern_id"),
                classification=result.get("classification"),
            )
            return result  # type: ignore[no-any-return]
        except Exception as e:  # noqa: BLE001
            logger.error("persist_pattern_failed", error=str(e))
            return None

    def _cache_pattern(self, pattern_id: str, pattern: dict[str, Any]) -> None:
        """Add pattern to LRU cache, evicting oldest if at capacity."""
        # Simple LRU: remove oldest entry if at max size
        if len(self._pattern_cache) >= self._pattern_cache_max_size:
            # Remove first (oldest) item
            oldest_key = next(iter(self._pattern_cache))
            del self._pattern_cache[oldest_key]

        self._pattern_cache[pattern_id] = pattern

    def recall_pattern(
        self,
        pattern_id: str,
        check_permissions: bool = True,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """Retrieve a pattern from long-term memory.

        Uses LRU cache for frequently accessed patterns to reduce I/O.

        Args:
            pattern_id: ID of pattern to retrieve
            check_permissions: Verify user has access to pattern
            use_cache: Whether to use/update the pattern cache (default: True)

        Returns:
            Pattern data with content and metadata, or None if not found

        """
        if not self._long_term:
            logger.error("long_term_memory_unavailable")
            return None

        # Check cache first (if enabled)
        if use_cache and pattern_id in self._pattern_cache:
            logger.debug("pattern_cache_hit", pattern_id=pattern_id)
            return self._pattern_cache[pattern_id]

        try:
            pattern = self._long_term.retrieve_pattern(
                pattern_id=pattern_id,
                user_id=self.user_id,
                check_permissions=check_permissions,
            )

            # Cache the result (if enabled and pattern found)
            if use_cache and pattern:
                self._cache_pattern(pattern_id, pattern)

            return pattern  # type: ignore[no-any-return]
        except Exception as e:  # noqa: BLE001
            logger.error("recall_pattern_failed", pattern_id=pattern_id, error=str(e))
            return None

    def delete_pattern(self, pattern_id: str, session_id: str = "") -> bool:
        """Delete a long-term pattern the current user owns.

        Delegates to the integration layer, which enforces creator-only
        deletion: it raises ``PermissionError`` when ``created_by`` is a
        different user and returns ``False`` when the pattern does not
        exist. The pattern is evicted from the local recall cache on a
        successful delete so a later ``recall_pattern`` does not serve a
        stale copy.

        Args:
            pattern_id: ID of the pattern to delete
            session_id: Session identifier for audit

        Returns:
            True if a pattern was deleted, False if none was found.

        Raises:
            PermissionError: If the current user does not own the pattern.
            ValueError: If ``pattern_id`` is empty.

        """
        from ..long_term_types import MemoryPermissionError

        if not self._long_term:
            logger.error("long_term_memory_unavailable")
            return False
        try:
            deleted = self._long_term.delete_pattern(pattern_id, self.user_id, session_id)
        except MemoryPermissionError as exc:
            # The integration layer raises its own (non-builtin) permission
            # type; surface the stable builtin PermissionError so callers
            # (e.g. the MCP forget handler) can catch it without importing
            # memory internals.
            raise PermissionError(str(exc)) from exc
        if deleted:
            self._pattern_cache.pop(pattern_id, None)
        return bool(deleted)

    def clear_pattern_cache(self) -> int:
        """Clear the pattern lookup cache.

        Returns:
            Number of entries cleared

        """
        count = len(self._pattern_cache)
        self._pattern_cache.clear()
        logger.debug("pattern_cache_cleared", entries=count)
        return count

    # =========================================================================
    # PATTERN SEARCH
    # =========================================================================

    def _score_pattern(
        self,
        pattern: dict[str, Any],
        query_lower: str,
        query_words: list[str],
    ) -> float:
        """Calculate relevance score for a pattern.

        Args:
            pattern: Pattern data dictionary
            query_lower: Lowercase query string
            query_words: Pre-split query words (length >= 3)

        Returns:
            Relevance score (0.0 if no match)

        """
        if not query_lower:
            return 1.0  # No query - all patterns have equal score

        content = str(pattern.get("content", "")).lower()
        metadata_str = str(pattern.get("metadata", {})).lower()

        score = 0.0

        # Exact phrase match in content (highest score)
        if query_lower in content:
            score += 10.0

        # Keyword matching (medium score)
        for word in query_words:
            if word in content:
                score += 2.0
            if word in metadata_str:
                score += 1.0

        return score

    def _filter_and_score_patterns(
        self,
        query: str | None,
        pattern_type: str | None,
        classification: "Classification | None",
    ) -> Iterator[tuple[float, dict[str, Any]]]:
        """Generator that filters and scores patterns.

        Memory-efficient: yields (score, pattern) tuples one at a time.
        Use with heapq.nlargest() for efficient top-N selection.

        Args:
            query: Search query (case-insensitive)
            pattern_type: Filter by pattern type
            classification: Filter by classification level

        Yields:
            Tuples of (score, pattern) for matching patterns

        """
        from ..long_term import Classification

        query_lower = query.lower() if query else ""
        query_words = [w for w in query_lower.split() if len(w) >= 3] if query else []

        for pattern in self._iter_all_patterns():
            # Apply filters
            if pattern_type and pattern.get("pattern_type") != pattern_type:
                continue

            if classification:
                pattern_class = pattern.get("classification")
                if isinstance(classification, Classification):
                    if pattern_class != classification.value:
                        continue
                elif pattern_class != classification:
                    continue

            # Calculate relevance score
            score = self._score_pattern(pattern, query_lower, query_words)

            # Skip if no matches found (when query is provided)
            if query and score == 0.0:
                continue

            yield (score, pattern)

    def search_patterns(
        self,
        query: str | None = None,
        pattern_type: str | None = None,
        classification: "Classification | None" = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search patterns in long-term memory with keyword matching and relevance scoring.

        Implements keyword-based search with:
        1. Full-text search in pattern content and metadata
        2. Filter by pattern_type and classification
        3. Relevance scoring (exact matches rank higher)
        4. Results sorted by relevance

        Memory-efficient: Uses generators and heapq.nlargest() to avoid
        loading all patterns into memory. Only keeps top N results.

        Args:
            query: Text to search for in pattern content (case-insensitive)
            pattern_type: Filter by pattern type (e.g., "meta_workflow_execution")
            classification: Filter by classification level
            limit: Maximum results to return

        Returns:
            List of matching patterns with metadata, sorted by relevance

        Example:
            >>> patterns = memory.search_patterns(
            ...     query="successful workflows",
            ...     pattern_type="meta_workflow_execution",
            ...     limit=5
            ... )

        """
        if not self._long_term:
            logger.debug("long_term_memory_unavailable")
            return []

        try:
            # Use heapq.nlargest for memory-efficient top-N selection
            # This avoids loading all patterns into memory at once
            scored_patterns = heapq.nlargest(
                limit,
                self._filter_and_score_patterns(query, pattern_type, classification),
                key=lambda x: x[0],
            )

            # Return patterns without scores
            return [pattern for _, pattern in scored_patterns]

        except Exception as e:  # noqa: BLE001
            logger.error("pattern_search_failed", error=str(e))
            return []

    # =========================================================================
    # PATTERN ITERATION (Internal Helpers)
    # =========================================================================

    def _get_storage_dir(self) -> Path | None:
        """Get the storage directory from long-term memory backend.

        Returns:
            Path to storage directory, or None if unavailable.

        """
        if not self._long_term:
            return None

        # Try different ways to access storage directory
        if hasattr(self._long_term, "storage_dir"):
            return Path(self._long_term.storage_dir)
        if hasattr(self._long_term, "storage"):
            if hasattr(self._long_term.storage, "storage_dir"):
                return Path(self._long_term.storage.storage_dir)
        elif hasattr(self._long_term, "_storage"):
            if hasattr(self._long_term._storage, "storage_dir"):
                return Path(self._long_term._storage.storage_dir)

        return None

    def _iter_all_patterns(self) -> Iterator[dict[str, Any]]:
        """Iterate over all patterns from long-term memory storage.

        Memory-efficient generator that yields patterns one at a time,
        avoiding loading all patterns into memory simultaneously.

        Yields:
            Pattern data dictionaries

        Note:
            This is O(1) memory vs O(n) for _get_all_patterns().
            Use this for large datasets or when streaming is acceptable.

        """
        storage_dir = self._get_storage_dir()
        if not storage_dir:
            logger.warning("cannot_access_storage_directory")
            return

        if not storage_dir.exists():
            return

        # Yield patterns one at a time (memory-efficient)
        for pattern_file in storage_dir.rglob("*.json"):
            try:
                with pattern_file.open("r", encoding="utf-8") as f:
                    yield json.load(f)
            except json.JSONDecodeError as e:
                logger.debug("pattern_json_decode_failed", file=str(pattern_file), error=str(e))
                continue
            except Exception as e:  # noqa: BLE001
                logger.debug("pattern_load_failed", file=str(pattern_file), error=str(e))
                continue
