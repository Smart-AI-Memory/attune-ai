"""Attune AI Memory Module

Unified two-tier memory system for AI agent collaboration:

SHORT-TERM MEMORY (Redis):
    - Agent coordination and working memory
    - TTL-based automatic expiration (5 min - 7 days)
    - Role-based access control (Observer -> Steward)
    - Pattern staging before validation

LONG-TERM MEMORY (Persistent):
    - Cross-session pattern storage
    - Classification-based access (PUBLIC/INTERNAL/SENSITIVE)
    - PII scrubbing and secrets detection
    - AES-256-GCM encryption for SENSITIVE patterns
    - Compliance: GDPR, HIPAA, SOC2

RECOMMENDED USAGE (Unified API):
    from attune.memory import UnifiedMemory

    # Initialize with environment auto-detection
    memory = UnifiedMemory(user_id="agent@company.com")

    # Short-term operations
    memory.stash("working_data", {"key": "value"})
    data = memory.retrieve("working_data")

    # Long-term operations
    result = memory.persist_pattern(
        content="Algorithm for X",
        pattern_type="algorithm",
    )
    pattern = memory.recall_pattern(result["pattern_id"])

    # Pattern promotion (short-term -> long-term)
    staged_id = memory.stage_pattern({"content": "..."})
    memory.promote_pattern(staged_id)

ADVANCED USAGE (Direct Access):
    from attune.memory import (
        # Short-term (Redis)
        RedisShortTermMemory,
        AccessTier,
        get_redis_memory,

        # Long-term (Persistent)
        SecureMemDocsIntegration,
        Classification,

        # Security
        PIIScrubber,
        SecretsDetector,
        AuditLogger,
    )

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .claude_memory import ClaudeMemoryConfig, ClaudeMemoryLoader
    from .config import (
        check_redis_connection,
        get_managed_redis,
        get_railway_redis,
        get_redis_config,
        get_redis_memory,
    )
    from .control_panel import ControlPanelConfig, MemoryControlPanel, MemoryStats
    from .cross_session import (
        BackgroundService,
        ConflictResult,
        ConflictStrategy,
        CrossSessionCoordinator,
        SessionInfo,
        SessionType,
        check_redis_cross_session_support,
        generate_agent_id,
    )
    from .features import (
        FeatureInfo,
        FeatureStatus,
        MemoryFeatures,
        RedisHealthReport,
        RedisHealthState,
        reset_redis_health_warnings,
    )
    from .file_session import FileSessionConfig, FileSessionMemory, get_file_session_memory
    from .long_term import (
        Classification,
        ClassificationRules,
        EncryptionManager,
        MemDocsStorage,
        PatternMetadata,
        SecureMemDocsIntegration,
        SecurePattern,
        SecurityError,
    )
    from .memory_tool import AttuneMemoryTool, make_memory_tool
    from .personal import PersonalMemory
    from .redis_bootstrap import (
        RedisStartMethod,
        RedisStatus,
        ensure_redis,
        get_redis_or_mock,
        stop_redis,
    )
    from .security import (
        AuditEvent,
        AuditLogger,
        PIIDetection,
        PIIPattern,
        PIIScrubber,
        SecretDetection,
        SecretsDetector,
        SecretType,
        SecurityViolation,
        Severity,
        detect_secrets,
    )
    from .short_term import RedisShortTermMemory
    from .summary_index import AgentContext, ConversationSummaryIndex
    from .types import (
        AccessTier,
        AgentCredentials,
        ConflictContext,
        PaginatedResult,
        RedisConfig,
        RedisMetrics,
        StagedPattern,
        TimeWindowQuery,
        TTLStrategy,
    )
    from .unified import Environment, MemoryConfig, UnifiedMemory

# Mapping of attribute names to (module_path, attribute_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # claude_memory
    "ClaudeMemoryConfig": (".claude_memory", "ClaudeMemoryConfig"),
    "ClaudeMemoryLoader": (".claude_memory", "ClaudeMemoryLoader"),
    # config
    "check_redis_connection": (".config", "check_redis_connection"),
    "get_managed_redis": (".config", "get_managed_redis"),
    "get_railway_redis": (".config", "get_railway_redis"),
    "get_redis_config": (".config", "get_redis_config"),
    "get_redis_memory": (".config", "get_redis_memory"),
    # control_panel
    "ControlPanelConfig": (".control_panel", "ControlPanelConfig"),
    "MemoryControlPanel": (".control_panel", "MemoryControlPanel"),
    "MemoryStats": (".control_panel", "MemoryStats"),
    # cross_session
    "BackgroundService": (".cross_session", "BackgroundService"),
    "ConflictResult": (".cross_session", "ConflictResult"),
    "ConflictStrategy": (".cross_session", "ConflictStrategy"),
    "CrossSessionCoordinator": (".cross_session", "CrossSessionCoordinator"),
    "SessionInfo": (".cross_session", "SessionInfo"),
    "SessionType": (".cross_session", "SessionType"),
    "check_redis_cross_session_support": (
        ".cross_session",
        "check_redis_cross_session_support",
    ),
    "generate_agent_id": (".cross_session", "generate_agent_id"),
    # features
    "FeatureInfo": (".features", "FeatureInfo"),
    "FeatureStatus": (".features", "FeatureStatus"),
    "MemoryFeatures": (".features", "MemoryFeatures"),
    "RedisHealthReport": (".features", "RedisHealthReport"),
    "RedisHealthState": (".features", "RedisHealthState"),
    "reset_redis_health_warnings": (".features", "reset_redis_health_warnings"),
    # file_session
    "FileSessionConfig": (".file_session", "FileSessionConfig"),
    "FileSessionMemory": (".file_session", "FileSessionMemory"),
    "get_file_session_memory": (".file_session", "get_file_session_memory"),
    # long_term
    "Classification": (".long_term", "Classification"),
    "ClassificationRules": (".long_term", "ClassificationRules"),
    "EncryptionManager": (".long_term", "EncryptionManager"),
    "MemDocsStorage": (".long_term", "MemDocsStorage"),
    "PatternMetadata": (".long_term", "PatternMetadata"),
    "SecureMemDocsIntegration": (".long_term", "SecureMemDocsIntegration"),
    "SecurePattern": (".long_term", "SecurePattern"),
    "SecurityError": (".long_term", "SecurityError"),
    "MemoryPermissionError": (".long_term", "PermissionError"),
    # redis_bootstrap
    "RedisStartMethod": (".redis_bootstrap", "RedisStartMethod"),
    "RedisStatus": (".redis_bootstrap", "RedisStatus"),
    "ensure_redis": (".redis_bootstrap", "ensure_redis"),
    "get_redis_or_mock": (".redis_bootstrap", "get_redis_or_mock"),
    "stop_redis": (".redis_bootstrap", "stop_redis"),
    # security
    "AuditEvent": (".security", "AuditEvent"),
    "AuditLogger": (".security", "AuditLogger"),
    "PIIDetection": (".security", "PIIDetection"),
    "PIIPattern": (".security", "PIIPattern"),
    "PIIScrubber": (".security", "PIIScrubber"),
    "SecretDetection": (".security", "SecretDetection"),
    "SecretsDetector": (".security", "SecretsDetector"),
    "SecretType": (".security", "SecretType"),
    "SecurityViolation": (".security", "SecurityViolation"),
    "Severity": (".security", "Severity"),
    "detect_secrets": (".security", "detect_secrets"),
    # short_term
    "RedisShortTermMemory": (".short_term", "RedisShortTermMemory"),
    # summary_index
    "AgentContext": (".summary_index", "AgentContext"),
    "ConversationSummaryIndex": (".summary_index", "ConversationSummaryIndex"),
    # types
    "AccessTier": (".types", "AccessTier"),
    "AgentCredentials": (".types", "AgentCredentials"),
    "ConflictContext": (".types", "ConflictContext"),
    "PaginatedResult": (".types", "PaginatedResult"),
    "RedisConfig": (".types", "RedisConfig"),
    "RedisMetrics": (".types", "RedisMetrics"),
    "StagedPattern": (".types", "StagedPattern"),
    "TimeWindowQuery": (".types", "TimeWindowQuery"),
    "TTLStrategy": (".types", "TTLStrategy"),
    "ShortTermSecurityError": (".types", "SecurityError"),
    # personal
    "PersonalMemory": (".personal", "PersonalMemory"),
    # unified
    "Environment": (".unified", "Environment"),
    "MemoryConfig": (".unified", "MemoryConfig"),
    "UnifiedMemory": (".unified", "UnifiedMemory"),
    # memory_tool — Anthropic Memory-tool backend bridge (lazy: anthropic
    # import stays deferred inside the factory)
    "AttuneMemoryTool": (".memory_tool", "AttuneMemoryTool"),
    "make_memory_tool": (".memory_tool", "make_memory_tool"),
}

# Cache for loaded attributes
_loaded_attrs: dict[str, object] = {}

#: Graph API removed in 10.0.0 (memorygraph-value-gate spec).
#: Curated memory now lives in plain .md files — see
#: docs/specs/memory-unification/.
_REMOVED_10_0_0 = frozenset(
    {
        "MemoryGraph",
        "Node",
        "NodeType",
        "BugNode",
        "PatternNode",
        "PerformanceNode",
        "VulnerabilityNode",
        "Edge",
        "EdgeType",
        "REVERSE_EDGE_TYPES",
        "WORKFLOW_EDGE_PATTERNS",
    }
)


def __getattr__(name: str) -> object:
    """Lazy import handler - loads memory submodules only when accessed."""
    if name in _REMOVED_10_0_0:
        raise AttributeError(
            f"'attune.memory.{name}' was removed in 10.0.0. Curated memory "
            "is now stored as plain .md files (~/.attune/memory/curated/) "
            "with Redis-derived serving — see docs/specs/memory-unification/."
        )
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]

        cache_key = f"{module_path}.{attr_name}"
        if cache_key in _loaded_attrs:
            return _loaded_attrs[cache_key]

        module = importlib.import_module(module_path, package="attune.memory")
        attr = getattr(module, attr_name)

        _loaded_attrs[cache_key] = attr
        return attr

    raise AttributeError(f"module 'attune.memory' has no attribute '{name}'")


def is_redis_available() -> bool:
    """Check if Redis subsystem is available without importing it.

    Returns:
        True if the redis package is importable, False otherwise.

    """
    try:
        importlib.import_module("redis")
        return True
    except ImportError:
        return False


__all__ = [
    "AccessTier",
    "AgentContext",
    "AgentCredentials",
    "AttuneMemoryTool",
    "AuditEvent",
    "AuditLogger",
    "BackgroundService",
    "Classification",
    "ClassificationRules",
    "ClaudeMemoryConfig",
    "ClaudeMemoryLoader",
    "ConflictContext",
    "ConflictResult",
    "ConflictStrategy",
    "ControlPanelConfig",
    "ConversationSummaryIndex",
    "CrossSessionCoordinator",
    "EncryptionManager",
    "Environment",
    "FeatureInfo",
    "FeatureStatus",
    "FileSessionConfig",
    "FileSessionMemory",
    "MemDocsStorage",
    "MemoryConfig",
    "MemoryControlPanel",
    "MemoryFeatures",
    "RedisHealthReport",
    "RedisHealthState",
    "MemoryPermissionError",
    "MemoryStats",
    "PIIDetection",
    "PIIPattern",
    "PIIScrubber",
    "PaginatedResult",
    "PersonalMemory",
    "PatternMetadata",
    "RedisConfig",
    "RedisMetrics",
    "RedisShortTermMemory",
    "RedisStartMethod",
    "RedisStatus",
    "SecretDetection",
    "SecretType",
    "SecretsDetector",
    "SecureMemDocsIntegration",
    "SecurePattern",
    "SecurityError",
    "SecurityViolation",
    "SessionInfo",
    "SessionType",
    "Severity",
    "ShortTermSecurityError",
    "StagedPattern",
    "TTLStrategy",
    "TimeWindowQuery",
    "UnifiedMemory",
    "check_redis_connection",
    "check_redis_cross_session_support",
    "detect_secrets",
    "ensure_redis",
    "generate_agent_id",
    "get_file_session_memory",
    "get_managed_redis",
    "get_railway_redis",
    "get_redis_config",
    "get_redis_memory",
    "get_redis_or_mock",
    "is_redis_available",
    "make_memory_tool",
    "reset_redis_health_warnings",
    "stop_redis",
]
