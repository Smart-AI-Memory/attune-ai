"""Unified Memory Interface for Attune AI

Provides a single API for both short-term (Redis) and long-term (persistent) memory,
with automatic pattern promotion and environment-aware storage backend selection.

Usage:
    from attune.memory import UnifiedMemory

    memory = UnifiedMemory(
        user_id="agent@company.com",
        environment="production",  # or "staging", "development"
    )

    # Short-term operations
    memory.stash("working_data", {"key": "value"})
    data = memory.retrieve("working_data")

    # Long-term operations
    result = memory.persist_pattern(content, pattern_type="algorithm")
    pattern = memory.recall_pattern(pattern_id)

    # Pattern promotion
    memory.promote_pattern(staged_pattern_id)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from .file_session import FileSessionMemory
from .long_term import LongTermMemory, SecureMemDocsIntegration
from .mixins import (
    BackendInitMixin,
    CapabilitiesMixin,
    HandoffAndExportMixin,
    LifecycleMixin,
    LongTermOperationsMixin,
    PatternPromotionMixin,
    ShortTermOperationsMixin,
)
from .redis_bootstrap import RedisStatus
from .short_term import (
    AccessTier,
    RedisShortTermMemory,
)
from .storage_backend import default_storage_dir

logger = structlog.get_logger(__name__)


class Environment(Enum):
    """Deployment environment for storage configuration."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class MemoryConfig:
    """Configuration for unified memory system."""

    # Environment
    environment: Environment = Environment.DEVELOPMENT

    # File-first architecture settings (always available)
    file_session_enabled: bool = True  # Use file-based session as primary
    file_session_dir: str = ".attune"  # Directory for file-based storage

    # Short-term memory settings (Redis - optional enhancement)
    redis_url: str | None = None
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_mock: bool = False
    redis_auto_start: bool = False  # File-first: Redis is optional
    redis_required: bool = False  # If True, fail without Redis
    default_ttl_seconds: int = 3600  # 1 hour

    # Long-term memory settings
    storage_dir: str = field(default_factory=default_storage_dir)
    encryption_enabled: bool = True

    # Claude memory settings
    claude_memory_enabled: bool = True
    load_enterprise_memory: bool = True
    load_project_memory: bool = True
    load_user_memory: bool = True

    # Compact state auto-generation
    auto_generate_compact_state: bool = True
    compact_state_path: str = ".claude/compact-state.md"

    @classmethod
    def from_environment(cls) -> "MemoryConfig":
        """Create configuration from environment variables.

        Environment Variables (ATTUNE_ prefix preferred, EMPATHY_ also accepted):
            ATTUNE_ENV: Environment (development/staging/production)
            ATTUNE_FILE_SESSION: Enable file-based session (true/false, default: true)
            ATTUNE_FILE_SESSION_DIR: Directory for file-based storage
            REDIS_URL: Redis connection URL
            ATTUNE_REDIS_MOCK: Use mock Redis (true/false)
            ATTUNE_REDIS_AUTO_START: Auto-start Redis (true/false, default: false)
            ATTUNE_REDIS_REQUIRED: Fail without Redis (true/false, default: false)
            ATTUNE_STORAGE_DIR: Long-term storage directory
            ATTUNE_ENCRYPTION: Enable encryption (true/false)
        """
        from urllib.parse import urlparse

        from attune.config.env_compat import get_attune_env
        from attune.memory.config import URL_VARS, resolve_redis_connection

        env_str = (get_attune_env("ENV", "development") or "development").lower()
        environment = (
            Environment(env_str)
            if env_str in [e.value for e in Environment]
            else Environment.DEVELOPMENT
        )
        _resolved = resolve_redis_connection()

        return cls(
            environment=environment,
            # File-first settings (always available)
            file_session_enabled=(get_attune_env("FILE_SESSION", "true") or "true").lower()
            == "true",
            file_session_dir=get_attune_env("FILE_SESSION_DIR", ".attune") or ".attune",
            # Redis settings (optional) — connection components from the
            # canonical resolver (rct-4). redis_url stays None unless a
            # URL var supplied it, preserving the explicit-URL gate in
            # backend_init_mixin; when set it carries merged credentials.
            redis_url=(_resolved.url if _resolved.source_map.get("url") in URL_VARS else None),
            redis_host=urlparse(_resolved.url).hostname or "127.0.0.1",
            redis_port=urlparse(_resolved.url).port or 6379,
            redis_mock=(get_attune_env("REDIS_MOCK", "") or "").lower() == "true",
            redis_auto_start=(get_attune_env("REDIS_AUTO_START", "false") or "false").lower()
            == "true",
            redis_required=(get_attune_env("REDIS_REQUIRED", "false") or "false").lower() == "true",
            # Long-term storage
            storage_dir=get_attune_env("STORAGE_DIR", "") or default_storage_dir(),
            encryption_enabled=(get_attune_env("ENCRYPTION", "true") or "true").lower() == "true",
            claude_memory_enabled=(get_attune_env("CLAUDE_MEMORY", "true") or "true").lower()
            == "true",
            # Compact state
            auto_generate_compact_state=(
                get_attune_env("AUTO_COMPACT_STATE", "true") or "true"
            ).lower()
            == "true",
            compact_state_path=get_attune_env("COMPACT_STATE_PATH", ".claude/compact-state.md")
            or ".claude/compact-state.md",
        )


@dataclass
class UnifiedMemory(
    BackendInitMixin,
    ShortTermOperationsMixin,
    LongTermOperationsMixin,
    PatternPromotionMixin,
    CapabilitiesMixin,
    HandoffAndExportMixin,
    LifecycleMixin,
):
    """Unified interface for short-term and long-term memory.

    Provides:
    - Short-term memory (Redis): Fast, TTL-based working memory
    - Long-term memory (Persistent): Cross-session pattern storage
    - Pattern promotion: Move validated patterns from short to long-term
    - Environment-aware configuration: Auto-detect storage backends
    """

    user_id: str
    config: MemoryConfig = field(default_factory=MemoryConfig.from_environment)
    access_tier: AccessTier = AccessTier.CONTRIBUTOR

    # Internal state
    _file_session: FileSessionMemory | None = field(default=None, init=False)  # Primary storage
    _short_term: RedisShortTermMemory | None = field(default=None, init=False)  # Optional Redis
    _long_term: SecureMemDocsIntegration | None = field(default=None, init=False)
    _simple_long_term: LongTermMemory | None = field(default=None, init=False)
    _redis_status: RedisStatus | None = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    # LRU cache for pattern lookups (pattern_id -> pattern_data)
    _pattern_cache: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _pattern_cache_max_size: int = field(default=100, init=False)

    def __post_init__(self):
        """Initialize memory backends based on configuration."""
        self._initialize_backends()
