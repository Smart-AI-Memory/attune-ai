"""Attune AI — AI developer workflows for Claude Code.

A Claude Code plugin for spec-driven development: code review, security
audit, test generation, refactor planning, and more — run as
auto-triggering skills and MCP tools, backed by multi-agent teams,
cost-aware model routing, retrieval grounding, and memory that persists
across sessions.

The plugin is the primary interface — install it in Claude Code (see
the README) and invoke ``/attune``, ``/security``, ``/smart-test``, etc.
The ``attune`` Python package exposes the supporting building blocks:

    from attune import UnifiedMemory, Classification

    # Two-tier memory (auto-detects environment)
    memory = UnifiedMemory(user_id="agent@company.com")

    # Short-term (Redis-backed, TTL-based)
    memory.stash("working_data", {"status": "processing"})
    data = memory.retrieve("working_data")

    # Long-term (persistent, classified)
    result = memory.persist_pattern(
        content="Optimization algorithm for X",
        pattern_type="algorithm",
        classification=Classification.INTERNAL,
    )
    pattern = memory.recall_pattern(result["pattern_id"])

KEY EXPORTS:
    - UnifiedMemory: Two-tier memory (short + long term)
    - MemoryConfig, Environment: Memory configuration
    - Classification, AccessTier: Security/access enums
    - AttuneConfig, EmpathyConfig: Configuration

REMOVED in 9.0.0 — legacy "Empathy" framework (see CHANGELOG):
    EmpathyOS, Level1Reactive…Level5Systems, FeedbackLoopDetector,
    LeveragePointAnalyzer. The 5-level maturity model is gone; attune-ai
    is the Claude Code workflow plugin. StateManager is now deprecated and
    will be removed in a future release.

REMOVED, pending release — the `attune.exceptions` hierarchy. Breaking,
so it rides the next MAJOR; see CHANGELOG [Unreleased]:
    EmpathyFrameworkError and its eight subclasses. They were the last
    unremoved surface of the 9.0.0 retirement — nothing raised them once
    their throwers were deleted. Note ValidationError went with them;
    attune.config.validation.ValidationError is a DIFFERENT, live class.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

try:
    from importlib.metadata import version as _get_version

    __version__ = _get_version("attune-ai")
except Exception:  # noqa: BLE001
    # INTENTIONAL: Fallback for dev installs without metadata
    __version__ = "dev"
__author__ = "Patrick Roebuck"
__email__ = "patrick.roebuck@smartaimemory.com"

# =============================================================================
# LAZY IMPORTS - Deferred loading for faster startup
# =============================================================================
# Instead of importing everything at module load, we use __getattr__ to load
# modules only when they're actually accessed. This reduces import time from
# ~1s to ~0.05s for simple use cases.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints for IDE support (not evaluated at runtime)
    from .agent_monitoring import AgentMetrics, AgentMonitor, TeamMetrics
    from .config import AttuneConfig, EmpathyConfig, load_config
    from .logging_config import LoggingConfig, get_logger
    from .memory import (
        AccessTier,
        AgentCredentials,
        AuditEvent,
        AuditLogger,
        Classification,
        ClassificationRules,
        ClaudeMemoryConfig,
        ClaudeMemoryLoader,
        ConflictContext,
        EncryptionManager,
        Environment,
        MemDocsStorage,
        MemoryConfig,
        MemoryPermissionError,
        PatternMetadata,
        PIIDetection,
        PIIPattern,
        PIIScrubber,
        RedisShortTermMemory,
        SecretDetection,
        SecretsDetector,
        SecretType,
        SecureMemDocsIntegration,
        SecurePattern,
        SecurityError,
        SecurityViolation,
        Severity,
        StagedPattern,
        TTLStrategy,
        UnifiedMemory,
        check_redis_connection,
        detect_secrets,
        get_managed_redis,
        get_railway_redis,
        get_redis_config,
        get_redis_memory,
    )
    from .pattern_library import Pattern, PatternLibrary, PatternMatch
    from .persistence import MetricsCollector, PatternPersistence, StateManager

# Mapping of attribute names to their module paths
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # agent_monitoring
    "AgentMetrics": (".agent_monitoring", "AgentMetrics"),
    "AgentMonitor": (".agent_monitoring", "AgentMonitor"),
    "TeamMetrics": (".agent_monitoring", "TeamMetrics"),
    # config
    "AttuneConfig": (".config", "AttuneConfig"),
    "EmpathyConfig": (".config", "EmpathyConfig"),
    "load_config": (".config", "load_config"),
    # coordination — removed in v6.8.0 (see src/attune/coordination.py shim)
    # core — EmpathyOS removed in v9.0.0
    # exceptions — removed (legacy "Empathy" surface); see CHANGELOG
    # feedback_loops, levels, leverage_points — removed in v9.0.0
    # logging_config
    "LoggingConfig": (".logging_config", "LoggingConfig"),
    "get_logger": (".logging_config", "get_logger"),
    # memory module
    "AccessTier": (".memory", "AccessTier"),
    "AgentCredentials": (".memory", "AgentCredentials"),
    "AuditEvent": (".memory", "AuditEvent"),
    "AuditLogger": (".memory", "AuditLogger"),
    "Classification": (".memory", "Classification"),
    "ClassificationRules": (".memory", "ClassificationRules"),
    "ClaudeMemoryConfig": (".memory", "ClaudeMemoryConfig"),
    "ClaudeMemoryLoader": (".memory", "ClaudeMemoryLoader"),
    "ConflictContext": (".memory", "ConflictContext"),
    "EncryptionManager": (".memory", "EncryptionManager"),
    "Environment": (".memory", "Environment"),
    "MemDocsStorage": (".memory", "MemDocsStorage"),
    "MemoryConfig": (".memory", "MemoryConfig"),
    "MemoryPermissionError": (".memory", "MemoryPermissionError"),
    "PatternMetadata": (".memory", "PatternMetadata"),
    "PIIDetection": (".memory", "PIIDetection"),
    "PIIPattern": (".memory", "PIIPattern"),
    "PIIScrubber": (".memory", "PIIScrubber"),
    "RedisShortTermMemory": (".memory", "RedisShortTermMemory"),
    "SecretDetection": (".memory", "SecretDetection"),
    "SecretsDetector": (".memory", "SecretsDetector"),
    "SecretType": (".memory", "SecretType"),
    "SecureMemDocsIntegration": (".memory", "SecureMemDocsIntegration"),
    "SecurePattern": (".memory", "SecurePattern"),
    "SecurityError": (".memory", "SecurityError"),
    "SecurityViolation": (".memory", "SecurityViolation"),
    "Severity": (".memory", "Severity"),
    "StagedPattern": (".memory", "StagedPattern"),
    "TTLStrategy": (".memory", "TTLStrategy"),
    "UnifiedMemory": (".memory", "UnifiedMemory"),
    "check_redis_connection": (".memory", "check_redis_connection"),
    "detect_secrets": (".memory", "detect_secrets"),
    "get_managed_redis": (".memory", "get_managed_redis"),
    "get_railway_redis": (".memory", "get_railway_redis"),
    "get_redis_config": (".memory", "get_redis_config"),
    "get_redis_memory": (".memory", "get_redis_memory"),
    # pattern_library
    "Pattern": (".pattern_library", "Pattern"),
    "PatternLibrary": (".pattern_library", "PatternLibrary"),
    "PatternMatch": (".pattern_library", "PatternMatch"),
    # persistence
    "MetricsCollector": (".persistence", "MetricsCollector"),
    "PatternPersistence": (".persistence", "PatternPersistence"),
    "StateManager": (".persistence", "StateManager"),
}

# Cache for loaded modules
_loaded_modules: dict[str, object] = {}


# Legacy "Empathy" framework surface. The EmpathyOS core + 5-level
# maturity model were REMOVED in 9.0.0. StateManager is the last vestige
# still importable; it is not used by the Claude Code workflow plugin at
# runtime and is slated for removal in a future release. Accessing it
# emits DeprecationWarning. See CHANGELOG and
# the EmpathyOS retirement spec under docs/specs/.
_DEPRECATED_FRAMEWORK: frozenset[str] = frozenset(
    {
        "StateManager",
    }
)


def __getattr__(name: str) -> object:
    """Lazy import handler - loads modules only when accessed."""
    if name in _LAZY_IMPORTS:
        if name in _DEPRECATED_FRAMEWORK:
            import warnings

            warnings.warn(
                f"attune.{name} belongs to the legacy Empathy framework and is "
                "deprecated. attune-ai now focuses on the Claude Code workflow "
                "plugin (MCP tools), which does not use it. The framework API "
                "will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        module_path, attr_name = _LAZY_IMPORTS[name]

        # Check cache first
        cache_key = f"{module_path}.{attr_name}"
        if cache_key in _loaded_modules:
            return _loaded_modules[cache_key]

        # Import the module and get the attribute
        import importlib

        module = importlib.import_module(module_path, package="attune")
        attr = getattr(module, attr_name)

        # Cache and return
        _loaded_modules[cache_key] = attr
        return attr

    raise AttributeError(f"module 'attune' has no attribute '{name}'")


__all__ = [
    "AccessTier",
    "AgentCredentials",
    "AgentMetrics",
    # Monitoring (Multi-Agent)
    "AgentMonitor",
    "AuditEvent",
    # Security - Audit
    "AuditLogger",
    "Classification",
    "ClassificationRules",
    # Claude Memory
    "ClaudeMemoryConfig",
    "ClaudeMemoryLoader",
    "ConflictContext",
    # Configuration
    "AttuneConfig",
    "EmpathyConfig",
    "EncryptionManager",
    "Environment",
    "LoggingConfig",
    "MemDocsStorage",
    "MemoryConfig",
    "MemoryPermissionError",
    "MetricsCollector",
    "PIIDetection",
    "PIIPattern",
    # Security - PII
    "PIIScrubber",
    "Pattern",
    # Pattern Library
    "PatternLibrary",
    "PatternMatch",
    "PatternMetadata",
    # Persistence
    "PatternPersistence",
    # Redis Short-Term Memory
    "RedisShortTermMemory",
    "SecretDetection",
    "SecretType",
    # Security - Secrets
    "SecretsDetector",
    # Long-term Memory
    "SecureMemDocsIntegration",
    "SecurePattern",
    "SecurityError",
    "SecurityViolation",
    "Severity",
    "StagedPattern",
    "StateManager",
    "TTLStrategy",
    "TeamMetrics",
    # Unified Memory Interface
    "UnifiedMemory",
    "check_redis_connection",
    "detect_secrets",
    # Logging
    "get_logger",
    "get_managed_redis",
    "get_railway_redis",
    "get_redis_config",
    # Redis Configuration
    "get_redis_memory",
    "load_config",
]
