"""Working memory operations - stash and retrieve.

This module provides the primary interface for storing and retrieving
agent working memory:
- Stash: Store data with optional TTL and metadata
- Retrieve: Get data by key
- Clear: Remove all working memory for an agent

Key Prefix: PREFIX_WORKING = "empathy:working:"

Classes:
    WorkingMemory: Core stash/retrieve operations

Example:
    >>> from attune.memory.short_term.working import WorkingMemory
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> # Typically composed into RedisShortTermMemory facade
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> working = WorkingMemory(base_ops, security_sanitizer)
    >>> working.stash("key", {"data": 123}, creds)
    >>> result = working.retrieve("key", creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.types import (
    AgentCredentials,
    TTLStrategy,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations
    from attune.memory.short_term.security import DataSanitizer

logger = structlog.get_logger(__name__)


class WorkingMemory:
    """Working memory operations for agent data storage.

    Provides stash (store) and retrieve operations with:
    - Access control based on agent credentials
    - Optional PII scrubbing and secrets detection
    - Configurable TTL strategies
    - Agent-scoped key namespacing

    The class is designed to be composed with BaseOperations and
    DataSanitizer for dependency injection.

    Attributes:
        PREFIX_WORKING: Key prefix for working memory namespace

    Example:
        >>> working = WorkingMemory(base_ops, sanitizer)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> working.stash("analysis", {"score": 95}, creds)
        True
        >>> working.retrieve("analysis", creds)
        {'score': 95}

    """

    PREFIX_WORKING = "empathy:working:"

    def __init__(
        self,
        base: BaseOperations,
        sanitizer: DataSanitizer | None = None,
    ) -> None:
        """Initialize working memory operations.

        Args:
            base: BaseOperations instance for storage access
            sanitizer: Optional DataSanitizer for PII/secrets handling

        """
        self._base = base
        self._sanitizer = sanitizer

    def stash(
        self,
        key: str,
        data: Any,
        credentials: AgentCredentials,
        ttl: TTLStrategy = TTLStrategy.WORKING_RESULTS,
        skip_sanitization: bool = False,
    ) -> bool:
        """Stash data in short-term memory.

        Stores data with automatic TTL expiration and optional
        security sanitization (PII scrubbing, secrets detection).

        Args:
            key: Unique key for the data
            data: Data to store (will be JSON serialized)
            credentials: Agent credentials for access control
            ttl: Time-to-live strategy (default: WORKING_RESULTS)
            skip_sanitization: Skip PII scrubbing and secrets detection

        Returns:
            True if successful

        Raises:
            ValueError: If key is empty or invalid
            PermissionError: If credentials lack write access
            SecurityError: If secrets are detected (when enabled)

        Note:
            PII (emails, SSNs, etc.) is automatically scrubbed unless
            skip_sanitization=True. Secrets block storage by default.

        Example:
            >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
            >>> working.stash("analysis_v1", {"findings": [...]}, creds)
            True

        """
        # Pattern 1: String ID validation
        if not key or not key.strip():
            raise ValueError(f"key cannot be empty. Got: {key!r}")

        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} (Tier {credentials.tier.name}) "
                "cannot write to memory. Requires CONTRIBUTOR or higher.",
            )

        # Sanitize data (PII scrubbing + secrets detection)
        pii_count = 0
        if not skip_sanitization and self._sanitizer is not None:
            data, pii_count = self._sanitizer.sanitize(data)
            if pii_count > 0:
                logger.info(
                    "stash_pii_scrubbed",
                    key=key,
                    agent_id=credentials.agent_id,
                    pii_count=pii_count,
                )

        full_key = f"{self.PREFIX_WORKING}{credentials.agent_id}:{key}"
        payload = {
            "data": data,
            "agent_id": credentials.agent_id,
            "stashed_at": datetime.now().isoformat(),
        }
        return self._base._set(full_key, json.dumps(payload), ttl.value)

    def retrieve(
        self,
        key: str,
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from short-term memory.

        Args:
            key: Key to retrieve
            credentials: Agent credentials
            agent_id: Owner agent ID (defaults to credentials agent)

        Returns:
            Retrieved data or None if not found

        Raises:
            ValueError: If key is empty or invalid

        Example:
            >>> data = working.retrieve("analysis_v1", creds)
            >>> if data:
            ...     print(f"Found: {data}")

        """
        # Pattern 1: String ID validation
        if not key or not key.strip():
            raise ValueError(f"key cannot be empty. Got: {key!r}")

        owner = agent_id or credentials.agent_id
        full_key = f"{self.PREFIX_WORKING}{owner}:{key}"
        raw = self._base._get(full_key)

        if raw is None:
            return None

        payload = json.loads(raw)
        return payload.get("data")

    def clear(self, credentials: AgentCredentials) -> int:
        """Clear all working memory for an agent.

        Removes all keys in the working memory namespace for
        the given agent.

        Args:
            credentials: Agent credentials (must own the memory or be Steward)

        Returns:
            Number of keys deleted

        Example:
            >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
            >>> deleted = working.clear(creds)
            >>> print(f"Deleted {deleted} keys")

        """
        pattern = f"{self.PREFIX_WORKING}{credentials.agent_id}:*"
        keys = self._base._keys(pattern)
        return self._base._delete_many(keys)

    def exists(
        self,
        key: str,
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> bool:
        """Check if a key exists in working memory.

        Args:
            key: Key to check
            credentials: Agent credentials
            agent_id: Owner agent ID (defaults to credentials agent)

        Returns:
            True if key exists

        """
        if not key or not key.strip():
            return False

        owner = agent_id or credentials.agent_id
        full_key = f"{self.PREFIX_WORKING}{owner}:{key}"
        return self._base._get(full_key) is not None

    def list_keys(self, credentials: AgentCredentials) -> list[str]:
        """List all working memory keys for an agent.

        Args:
            credentials: Agent credentials

        Returns:
            List of key names (without prefix)

        """
        pattern = f"{self.PREFIX_WORKING}{credentials.agent_id}:*"
        keys = self._base._keys(pattern)
        prefix_len = len(f"{self.PREFIX_WORKING}{credentials.agent_id}:")
        return [k[prefix_len:] for k in keys]
