"""Memory Control Panel for Attune AI

Enterprise-grade control panel for managing AI memory systems.
Provides both programmatic API and CLI interface.

Features:
- Redis lifecycle management (start/stop/status)
- Memory statistics and health monitoring
- Pattern management (list, search, delete)
- Configuration management
- Export/import capabilities

Usage (Python API):
    from attune.memory import MemoryControlPanel

    panel = MemoryControlPanel()
    print(panel.status())
    panel.start_redis()
    panel.show_statistics()

Usage (CLI):
    python -m attune.memory.control_panel status
    python -m attune.memory.control_panel start
    python -m attune.memory.control_panel stats
    python -m attune.memory.control_panel patterns --list

IMPORTANT: This module re-exports all public symbols from submodules for
backward compatibility. All symbols remain importable from attune.memory.control_panel.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

# Re-export API handler and server for backward compatibility
from .control_panel_api import MemoryAPIHandler, run_api_server  # noqa: F401

# Re-export display functions and CLI entry point for backward compatibility
from .control_panel_display import (  # noqa: F401
    _configure_logging,
    main,
    print_health,
    print_stats,
    print_status,
)
from .control_panel_support import APIKeyAuth, MemoryStats, RateLimiter  # noqa: F401 - re-exported
from .control_panel_validation import (  # noqa: F401 - re-exported for backward compat
    PATTERN_ID_ALT_REGEX,
    PATTERN_ID_REGEX,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    _validate_agent_id,
    _validate_classification,
    _validate_file_path,
    _validate_pattern_id,
)
from .long_term import Classification, SecureMemDocsIntegration
from .redis_bootstrap import (
    RedisStartMethod,
    RedisStatus,
    _check_redis_running,
    ensure_redis,
    stop_redis,
)
from .short_term import RedisShortTermMemory
from .storage_backend import default_storage_dir
from .types import AccessTier, AgentCredentials

# Suppress noisy warnings in CLI mode
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

# Version
__version__ = "2.2.0"

logger = structlog.get_logger(__name__)


@dataclass
class ControlPanelConfig:
    """Configuration for control panel."""

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    storage_dir: str = field(default_factory=default_storage_dir)
    audit_dir: str = "./logs"
    auto_start_redis: bool = True


class MemoryControlPanel:
    """Enterprise control panel for Empathy memory management.

    Provides unified management interface for:
    - Short-term memory (Redis)
    - Long-term memory (MemDocs/file storage)
    - Security and compliance controls

    Example:
        >>> panel = MemoryControlPanel()
        >>> status = panel.status()
        >>> print(f"Redis: {status['redis']['status']}")
        >>> print(f"Patterns: {status['long_term']['pattern_count']}")

    """

    def __init__(self, config: ControlPanelConfig | None = None):
        """Initialize control panel.

        Args:
            config: Configuration options (uses defaults if None)

        """
        self.config = config or ControlPanelConfig()
        self._redis_status: RedisStatus | None = None
        self._short_term: RedisShortTermMemory | None = None
        self._long_term: SecureMemDocsIntegration | None = None

    def status(self) -> dict[str, Any]:
        """Get comprehensive status of memory system.

        Returns:
            Dictionary with status of all memory components

        """
        redis_running = _check_redis_running(self.config.redis_host, self.config.redis_port)

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "redis": {
                "status": "running" if redis_running else "stopped",
                "host": self.config.redis_host,
                "port": self.config.redis_port,
                "method": self._redis_status.method.value if self._redis_status else "unknown",
            },
            "long_term": {
                "status": (
                    "available" if Path(self.config.storage_dir).exists() else "not_initialized"
                ),
                "storage_dir": self.config.storage_dir,
                "pattern_count": self._count_patterns(),
            },
            "config": {
                "auto_start_redis": self.config.auto_start_redis,
                "audit_dir": self.config.audit_dir,
            },
        }

        return result

    def start_redis(self, verbose: bool = True) -> RedisStatus:
        """Start Redis if not running.

        Args:
            verbose: Print status messages

        Returns:
            RedisStatus with result

        """
        self._redis_status = ensure_redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            auto_start=True,
            verbose=verbose,
        )
        return self._redis_status

    def stop_redis(self) -> bool:
        """Stop Redis if we started it.

        Returns:
            True if stopped successfully

        """
        if self._redis_status and self._redis_status.method != RedisStartMethod.ALREADY_RUNNING:
            return stop_redis(self._redis_status.method)
        return False

    def get_statistics(self) -> MemoryStats:
        """Collect comprehensive statistics.

        Returns:
            MemoryStats with all metrics

        """
        start_time = time.perf_counter()
        stats = MemoryStats(collected_at=datetime.now(timezone.utc).isoformat())

        # Redis stats
        redis_running = _check_redis_running(self.config.redis_host, self.config.redis_port)
        stats.redis_available = redis_running

        if redis_running:
            try:
                memory = self._get_short_term()

                # Measure Redis ping latency
                ping_start = time.perf_counter()
                redis_stats = memory.get_stats()
                stats.redis_ping_ms = (time.perf_counter() - ping_start) * 1000

                stats.redis_method = redis_stats.get("mode", "redis")
                stats.redis_keys_total = redis_stats.get("total_keys", 0)
                stats.redis_keys_working = redis_stats.get("working_keys", 0)
                stats.redis_keys_staged = redis_stats.get("staged_keys", 0)
                stats.redis_memory_used = redis_stats.get("used_memory", "0")
            except Exception as e:  # noqa: BLE001
                logger.warning("redis_stats_failed", error=str(e))

        # Long-term stats
        storage_path = Path(self.config.storage_dir)
        if storage_path.exists():
            stats.long_term_available = True

            # Calculate storage size
            try:
                stats.storage_bytes = sum(
                    f.stat().st_size for f in storage_path.glob("**/*") if f.is_file()
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("storage_size_calculation_failed", error=str(e))
                stats.storage_bytes = 0

            try:
                long_term = self._get_long_term()
                lt_stats = long_term.get_statistics()
                stats.patterns_total = lt_stats.get("total_patterns", 0)
                stats.patterns_public = lt_stats.get("by_classification", {}).get("PUBLIC", 0)
                stats.patterns_internal = lt_stats.get("by_classification", {}).get("INTERNAL", 0)
                stats.patterns_sensitive = lt_stats.get("by_classification", {}).get("SENSITIVE", 0)
                stats.patterns_encrypted = lt_stats.get("encrypted_count", 0)
            except Exception as e:  # noqa: BLE001
                logger.warning("long_term_stats_failed", error=str(e))

        # Total collection time
        stats.collection_time_ms = (time.perf_counter() - start_time) * 1000

        return stats

    def list_patterns(
        self,
        classification: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List patterns in long-term storage.

        Args:
            classification: Filter by classification (PUBLIC/INTERNAL/SENSITIVE)
            limit: Maximum patterns to return

        Returns:
            List of pattern summaries

        Raises:
            ValueError: If classification is invalid or limit is out of range

        """
        # Validate classification
        if not _validate_classification(classification):
            raise ValueError(
                f"Invalid classification '{classification}'. "
                f"Must be PUBLIC, INTERNAL, or SENSITIVE.",
            )

        # Validate limit range
        if limit < 1:
            raise ValueError(f"limit must be positive, got {limit}")

        if limit > 10000:
            raise ValueError(f"limit too large (max 10000), got {limit}")

        long_term = self._get_long_term()

        class_filter = None
        if classification:
            class_filter = Classification[classification.upper()]

        # Use admin user for listing
        patterns = long_term.list_patterns(
            user_id="admin@system",
            classification=class_filter,
        )

        return patterns[:limit]

    def delete_pattern(self, pattern_id: str, user_id: str = "admin@system") -> bool:
        """Delete a pattern from long-term storage.

        Args:
            pattern_id: Pattern to delete
            user_id: User performing deletion (for audit)

        Returns:
            True if deleted

        Raises:
            ValueError: If pattern_id or user_id format is invalid

        """
        # Validate pattern_id
        if not _validate_pattern_id(pattern_id):
            raise ValueError(f"Invalid pattern_id format: {pattern_id}")

        # Validate user_id (reuse agent_id validation - same format)
        if not _validate_agent_id(user_id):
            raise ValueError(f"Invalid user_id format: {user_id}")

        long_term = self._get_long_term()
        try:
            return long_term.delete_pattern(pattern_id, user_id)
        except Exception as e:  # noqa: BLE001
            logger.error("delete_pattern_failed", pattern_id=pattern_id, error=str(e))
            return (
                False  # Graceful degradation - validation errors raise, storage errors return False
            )

    def clear_short_term(self, agent_id: str = "admin") -> int:
        """Clear all short-term memory for an agent.

        Args:
            agent_id: Agent whose memory to clear

        Returns:
            Number of keys deleted

        Raises:
            ValueError: If agent_id format is invalid

        """
        # Validate agent_id
        if not _validate_agent_id(agent_id):
            raise ValueError(f"Invalid agent_id format: {agent_id}")

        memory = self._get_short_term()
        creds = AgentCredentials(agent_id=agent_id, tier=AccessTier.STEWARD)
        return memory.clear_working_memory(creds)

    def export_patterns(self, output_path: str, classification: str | None = None) -> int:
        """Export patterns to JSON file.

        Args:
            output_path: Path to output file
            classification: Filter by classification

        Returns:
            Number of patterns exported

        Raises:
            ValueError: If output_path is invalid, classification invalid, or path is unsafe

        """
        # Validate file path to prevent path traversal attacks
        validated_path = _validate_file_path(output_path)

        # Validate classification (list_patterns will also validate, but do it early)
        if not _validate_classification(classification):
            raise ValueError(
                f"Invalid classification '{classification}'. "
                f"Must be PUBLIC, INTERNAL, or SENSITIVE.",
            )

        patterns = self.list_patterns(classification=classification)

        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "classification_filter": classification,
            "pattern_count": len(patterns),
            "patterns": patterns,
        }

        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        return len(patterns)

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status with recommendations

        """
        status = self.status()
        stats = self.get_statistics()

        checks: list[dict[str, str]] = []
        recommendations: list[str] = []
        health: dict[str, Any] = {
            "overall": "healthy",
            "checks": checks,
            "recommendations": recommendations,
        }

        # Check Redis
        if status["redis"]["status"] == "running":
            checks.append({"name": "redis", "status": "pass", "message": "Redis is running"})
        else:
            checks.append({"name": "redis", "status": "warn", "message": "Redis not running"})
            recommendations.append("Start Redis for multi-agent coordination")
            health["overall"] = "degraded"

        # Check long-term storage
        if status["long_term"]["status"] == "available":
            checks.append({"name": "long_term", "status": "pass", "message": "Storage available"})
        else:
            checks.append(
                {"name": "long_term", "status": "warn", "message": "Storage not initialized"},
            )
            recommendations.append("Initialize long-term storage directory")
            health["overall"] = "degraded"

        # Check pattern count
        if stats.patterns_total > 0:
            checks.append(
                {
                    "name": "patterns",
                    "status": "pass",
                    "message": f"{stats.patterns_total} patterns stored",
                },
            )
        else:
            checks.append(
                {"name": "patterns", "status": "info", "message": "No patterns stored yet"},
            )

        # Check encryption
        if stats.patterns_sensitive > 0 and stats.patterns_encrypted < stats.patterns_sensitive:
            checks.append(
                {
                    "name": "encryption",
                    "status": "fail",
                    "message": "Some sensitive patterns are not encrypted",
                },
            )
            recommendations.append("Enable encryption for sensitive patterns")
            health["overall"] = "unhealthy"
        elif stats.patterns_sensitive > 0:
            checks.append(
                {
                    "name": "encryption",
                    "status": "pass",
                    "message": "All sensitive patterns encrypted",
                },
            )

        return health

    def _get_short_term(self) -> RedisShortTermMemory:
        """Get or create short-term memory instance."""
        if self._short_term is None:
            redis_running = _check_redis_running(self.config.redis_host, self.config.redis_port)
            self._short_term = RedisShortTermMemory(
                host=self.config.redis_host,
                port=self.config.redis_port,
                use_mock=not redis_running,
            )
        return self._short_term

    def _get_long_term(self) -> SecureMemDocsIntegration:
        """Get or create long-term memory instance."""
        if self._long_term is None:
            self._long_term = SecureMemDocsIntegration(
                storage_dir=self.config.storage_dir,
                audit_log_dir=self.config.audit_dir,
                enable_encryption=True,
            )
        return self._long_term

    def _count_patterns(self) -> int:
        """Count patterns in storage.

        Returns:
            Number of pattern files, or 0 if counting fails

        """
        storage_path = Path(self.config.storage_dir)
        if not storage_path.exists():
            return 0

        try:
            return len(list(storage_path.glob("*.json")))
        except (OSError, PermissionError) as e:
            logger.debug("pattern_count_failed", error=str(e))
            return 0


if __name__ == "__main__":
    main()
