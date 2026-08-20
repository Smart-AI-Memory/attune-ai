"""Memory types and data classes for Attune AI.

This module contains shared data structures used by the memory subsystem:
- Access control (AccessTier, AgentCredentials)
- TTL strategies (TTLStrategy)
- Configuration (RedisConfig)
- Metrics (RedisMetrics)
- Query types (PaginatedResult, TimeWindowQuery)
- Domain objects (StagedPattern, ConflictContext)
- Exceptions (SecurityError)

These types are independent of Redis and can be imported without the redis package.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, TypeVar

logger = logging.getLogger(__name__)


class _FromDict(Protocol):
    """A model that can be rebuilt from its stored dict form."""

    @classmethod
    def from_dict(cls, data: dict) -> Any: ...


_Model = TypeVar("_Model", bound=_FromDict)


def parse_stored_record(model: type[_Model], raw: Any, *, key: str = "") -> _Model | None:
    """Rebuild a stored record, or None when the bytes cannot be read.

    Library-review I-4: stores did ``Model.from_dict(json.loads(raw))``
    with the parse and the subscripting in different functions, so
    neither the caller's ``except`` nor the dict-guard gate could see
    the hazard. One legacy or hand-edited value then raised out of a
    read, and since the read backs promotion, *every* promotion was
    blocked by one bad key — a P15 violation (the memory layer degrades,
    it never blocks).

    Three failure modes collapse to None here: unparseable JSON, a
    parsed value that is not a mapping (a list subscripted by string key
    raises ``TypeError``, which callers' except-tuples missed), and a
    record whose fields ``from_dict`` rejects.

    Args:
        model: The dataclass to rebuild; must expose ``from_dict``.
        raw: The stored JSON text (``str`` or ``bytes``).
        key: Storage key, for the log line only.

    Returns:
        The rebuilt model, or None — never raises.
    """
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:  # ValueError covers JSONDecodeError
        logger.warning("stored_record_unparseable model=%s key=%s: %s", model.__name__, key, exc)
        return None
    if not isinstance(data, dict):
        logger.warning(
            "stored_record_not_a_mapping model=%s key=%s got=%s",
            model.__name__,
            key,
            type(data).__name__,
        )
        return None
    try:
        return model.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("stored_record_rejected model=%s key=%s: %s", model.__name__, key, exc)
        return None


class AccessTier(Enum):
    """Role-based access tiers per EMPATHY_PHILOSOPHY.md

    Tier 1 - Observer: Read-only access to validated patterns
    Tier 2 - Contributor: Can stage patterns for validation
    Tier 3 - Validator: Can promote staged patterns to active
    Tier 4 - Steward: Full access including deprecation and audit
    """

    OBSERVER = 1
    CONTRIBUTOR = 2
    VALIDATOR = 3
    STEWARD = 4


class TTLStrategy(Enum):
    """TTL strategies for different memory types

    Per EMPATHY_PHILOSOPHY.md Section 9.3:
    - Working results: 1 hour
    - Staged patterns: 24 hours
    - Coordination signals: 5 minutes (REMOVED in v5.0 - see CoordinationSignals)
    - Conflict context: Until resolution
    """

    WORKING_RESULTS = 3600  # 1 hour
    STAGED_PATTERNS = 86400  # 24 hours
    # COORDINATION removed in v5.0 - use CoordinationSignals with custom TTLs
    CONFLICT_CONTEXT = 604800  # 7 days (fallback for unresolved)
    SESSION = 1800  # 30 minutes
    STREAM_ENTRY = 86400 * 7  # 7 days for audit stream entries
    TASK_QUEUE = 3600 * 4  # 4 hours for task queue items


@dataclass
class RedisConfig:
    """Enhanced Redis configuration with SSL and retry support.

    Supports:
    - Standard connections (host:port)
    - URL-based connections (redis://...)
    - SSL/TLS for managed services (rediss://...)
    - Sentinel for high availability
    - Connection pooling
    - Retry with exponential backoff
    """

    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0
    password: str | None = None
    use_mock: bool = False

    # Security settings
    pii_scrub_enabled: bool = True  # Scrub PII before storing (HIPAA/GDPR compliance)
    secrets_detection_enabled: bool = True  # Block storage of detected secrets

    # SSL/TLS settings
    ssl: bool = False
    ssl_cert_reqs: str | None = None  # "required", "optional", "none"
    ssl_ca_certs: str | None = None
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None

    # Connection pool settings
    max_connections: int = 10
    health_check_interval: int = 30  # Seconds between background PING on idle connections
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0

    # Retry settings
    retry_on_timeout: bool = True
    retry_max_attempts: int = 3
    retry_base_delay: float = 0.1  # seconds
    retry_max_delay: float = 2.0  # seconds

    # Local LRU cache settings (two-tier caching)
    local_cache_enabled: bool = True  # Enable local memory cache (reduces Redis network I/O)
    local_cache_size: int = 500  # Maximum number of cached keys (~50KB memory)

    # Sentinel settings (for HA)
    sentinel_hosts: list[tuple[str, int]] | None = None
    sentinel_master_name: str | None = None

    def to_redis_kwargs(self) -> dict:
        """Convert to redis.Redis constructor kwargs."""
        kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "password": self.password,
            "decode_responses": True,
            "max_connections": self.max_connections,
            "health_check_interval": self.health_check_interval,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "retry_on_timeout": self.retry_on_timeout,
        }

        if self.ssl:
            kwargs["ssl"] = True
            if self.ssl_cert_reqs:
                kwargs["ssl_cert_reqs"] = self.ssl_cert_reqs
            if self.ssl_ca_certs:
                kwargs["ssl_ca_certs"] = self.ssl_ca_certs
            if self.ssl_certfile:
                kwargs["ssl_certfile"] = self.ssl_certfile
            if self.ssl_keyfile:
                kwargs["ssl_keyfile"] = self.ssl_keyfile

        return kwargs


@dataclass
class RedisMetrics:
    """Metrics for Redis operations."""

    operations_total: int = 0
    operations_success: int = 0
    operations_failed: int = 0
    retries_total: int = 0
    latency_sum_ms: float = 0.0
    latency_max_ms: float = 0.0

    # Per-operation metrics
    stash_count: int = 0
    retrieve_count: int = 0
    publish_count: int = 0
    stream_append_count: int = 0

    # Security metrics
    pii_scrubbed_total: int = 0  # Total PII instances scrubbed
    pii_scrub_operations: int = 0  # Operations that had PII scrubbed
    secrets_blocked_total: int = 0  # Total secrets blocked from storage

    def record_operation(self, operation: str, latency_ms: float, success: bool = True) -> None:
        """Record an operation metric."""
        self.operations_total += 1
        self.latency_sum_ms += latency_ms
        self.latency_max_ms = max(self.latency_max_ms, latency_ms)

        if success:
            self.operations_success += 1
        else:
            self.operations_failed += 1

        # Track by operation type
        _OP_COUNTERS = {
            "stash": "stash_count",
            "retrieve": "retrieve_count",
            "publish": "publish_count",
            "stream_append": "stream_append_count",
        }
        attr = _OP_COUNTERS.get(operation)
        if attr:
            setattr(self, attr, getattr(self, attr) + 1)

    @property
    def latency_avg_ms(self) -> float:
        """Average latency in milliseconds."""
        if self.operations_total == 0:
            return 0.0
        return self.latency_sum_ms / self.operations_total

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.operations_total == 0:
            return 100.0
        return (self.operations_success / self.operations_total) * 100

    @property
    def total_requests(self) -> int:
        """Total requests (alias for operations_total for backward compatibility)."""
        return self.operations_total

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for reporting and serialization.

        Returns:
            Dictionary with keys: operations_total, operations_success,
            operations_failed, retries_total, latency_avg_ms, latency_max_ms,
            success_rate, by_operation, security.

        """
        return {
            "operations_total": self.operations_total,
            "operations_success": self.operations_success,
            "operations_failed": self.operations_failed,
            "retries_total": self.retries_total,
            "latency_avg_ms": round(self.latency_avg_ms, 2),
            "latency_max_ms": round(self.latency_max_ms, 2),
            "success_rate": round(self.success_rate, 2),
            "by_operation": {
                "stash": self.stash_count,
                "retrieve": self.retrieve_count,
                "publish": self.publish_count,
                "stream_append": self.stream_append_count,
            },
            "security": {
                "pii_scrubbed_total": self.pii_scrubbed_total,
                "pii_scrub_operations": self.pii_scrub_operations,
                "secrets_blocked_total": self.secrets_blocked_total,
            },
        }


@dataclass
class PaginatedResult:
    """Result of a paginated query."""

    items: list[Any]
    cursor: str
    has_more: bool
    total_scanned: int = 0


@dataclass
class TimeWindowQuery:
    """Query parameters for time-window operations."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100
    offset: int = 0

    @property
    def start_score(self) -> float:
        """Start timestamp as Redis score."""
        if self.start_time is None:
            return float("-inf")
        return self.start_time.timestamp()

    @property
    def end_score(self) -> float:
        """End timestamp as Redis score."""
        if self.end_time is None:
            return float("+inf")
        return self.end_time.timestamp()


@dataclass
class AgentCredentials:
    """Agent identity and access permissions"""

    agent_id: str
    tier: AccessTier
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def can_read(self) -> bool:
        """All tiers can read"""
        return True

    def can_stage(self) -> bool:
        """Contributor+ can stage patterns"""
        return self.tier.value >= AccessTier.CONTRIBUTOR.value

    def can_validate(self) -> bool:
        """Validator+ can promote patterns"""
        return self.tier.value >= AccessTier.VALIDATOR.value

    def can_administer(self) -> bool:
        """Only Stewards have full admin access"""
        return self.tier.value >= AccessTier.STEWARD.value


@dataclass
class StagedPattern:
    """Pattern awaiting validation"""

    pattern_id: str
    agent_id: str
    pattern_type: str
    name: str
    description: str
    code: str | None = None
    context: dict = field(default_factory=dict)
    confidence: float = 0.5
    staged_at: datetime = field(default_factory=datetime.now)
    interests: list[str] = field(default_factory=list)  # For negotiation

    def __post_init__(self):
        """Validate fields after initialization"""
        # Pattern 1: String ID validation
        if not self.pattern_id or not self.pattern_id.strip():
            raise ValueError(f"pattern_id cannot be empty. Got: {self.pattern_id!r}")
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError(f"agent_id cannot be empty. Got: {self.agent_id!r}")
        if not self.pattern_type or not self.pattern_type.strip():
            raise ValueError(f"pattern_type cannot be empty. Got: {self.pattern_type!r}")

        # Pattern 4: Range validation for confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Pattern 5: Type validation
        if not isinstance(self.context, dict):
            raise TypeError(f"context must be dict, got {type(self.context).__name__}")
        if not isinstance(self.interests, list):
            raise TypeError(f"interests must be list, got {type(self.interests).__name__}")

    def to_dict(self) -> dict:
        """Convert staged pattern to dictionary for serialization.

        Returns:
            Dictionary with keys: pattern_id, agent_id, pattern_type, name,
            description, code, context, confidence, staged_at, interests.

        """
        return {
            "pattern_id": self.pattern_id,
            "agent_id": self.agent_id,
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "context": self.context,
            "confidence": self.confidence,
            "staged_at": self.staged_at.isoformat(),
            "interests": self.interests,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StagedPattern":
        """Reconstruct StagedPattern from dictionary.

        Args:
            data: Dictionary with required keys: pattern_id, agent_id,
                pattern_type, name, description, staged_at.

        Returns:
            Reconstructed StagedPattern instance.

        Raises:
            KeyError: If required keys are missing.
            ValueError: If data format is invalid.

        """
        return cls(
            pattern_id=data["pattern_id"],
            agent_id=data["agent_id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            description=data["description"],
            code=data.get("code"),
            context=data.get("context", {}),
            confidence=data.get("confidence", 0.5),
            staged_at=datetime.fromisoformat(data["staged_at"]),
            interests=data.get("interests", []),
        )


@dataclass
class ConflictContext:
    """Context for principled negotiation

    Per Getting to Yes framework:
    - Positions: What each party says they want
    - Interests: Why they want it (underlying needs)
    - BATNA: Best Alternative to Negotiated Agreement
    """

    conflict_id: str
    positions: dict[str, Any]  # agent_id -> stated position
    interests: dict[str, list[str]]  # agent_id -> underlying interests
    batna: str | None = None  # Fallback strategy
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: str | None = None

    def to_dict(self) -> dict:
        """Convert conflict context to dictionary for serialization.

        Returns:
            Dictionary with keys: conflict_id, positions, interests,
            batna, created_at, resolved, resolution.

        """
        return {
            "conflict_id": self.conflict_id,
            "positions": self.positions,
            "interests": self.interests,
            "batna": self.batna,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConflictContext":
        """Reconstruct ConflictContext from dictionary.

        Args:
            data: Dictionary with required keys: conflict_id, positions,
                interests, created_at.

        Returns:
            Reconstructed ConflictContext instance.

        Raises:
            KeyError: If required keys are missing.
            ValueError: If data format is invalid.

        """
        return cls(
            conflict_id=data["conflict_id"],
            positions=data["positions"],
            interests=data["interests"],
            batna=data.get("batna"),
            created_at=datetime.fromisoformat(data["created_at"]),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
        )


class SecurityError(Exception):
    """Raised when a security policy is violated (e.g., secrets detected in data)."""


__all__ = [
    "AccessTier",
    "AgentCredentials",
    "ConflictContext",
    "PaginatedResult",
    "RedisConfig",
    "RedisMetrics",
    "SecurityError",
    "StagedPattern",
    "TTLStrategy",
    "TimeWindowQuery",
]
