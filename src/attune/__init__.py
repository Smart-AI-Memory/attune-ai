"""Attune AI - AI-Human Collaboration Library

A five-level maturity model for building AI systems that progress from
reactive responses to anticipatory problem prevention.

QUICK START:
    from attune import EmpathyOS

    # Create an EmpathyOS instance
    empathy = EmpathyOS(user_id="developer@company.com")

    # Use Level 4 (Anticipatory) for predictions
    response = empathy.level_4_anticipatory(
        user_input="How do I optimize database queries?",
        context={"domain": "software"},
        history=[]
    )

    print(f"Response: {response['response']}")
    print(f"Predictions: {response.get('predictions', [])}")

    # Store patterns in memory
    empathy.stash("session_context", {"topic": "database optimization"})
    empathy.persist_pattern(
        content="Query optimization technique",
        pattern_type="technique"
    )

MEMORY OPERATIONS:
    from attune import UnifiedMemory, Classification

    # Initialize unified memory (auto-detects environment)
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
    - EmpathyOS: Main orchestration class
    - UnifiedMemory: Two-tier memory (short + long term)
    - MemoryConfig, Environment: Memory configuration
    - Classification, AccessTier: Security/access enums
    - Level1-5 classes: Empathy level implementations

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

__version__ = "5.1.5"
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
    from .coordination import (
        AgentCoordinator,
        AgentTask,
        ConflictResolver,
        ResolutionResult,
        ResolutionStrategy,
        TeamPriorities,
        TeamSession,
    )
    from .core import EmpathyOS
    from .emergence import EmergenceDetector
    from .exceptions import (
        CollaborationStateError,
        ConfidenceThresholdError,
        EmpathyFrameworkError,
        EmpathyLevelError,
        FeedbackLoopError,
        LeveragePointError,
        PatternNotFoundError,
        TrustThresholdError,
        ValidationError,
    )
    from .feedback_loops import FeedbackLoopDetector
    from .levels import (
        Level1Reactive,
        Level2Guided,
        Level3Proactive,
        Level4Anticipatory,
        Level5Systems,
    )
    from .leverage_points import LeveragePointAnalyzer
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
        get_railway_redis,
        get_redis_config,
        get_redis_memory,
    )
    from .pattern_library import Pattern, PatternLibrary, PatternMatch
    from .persistence import MetricsCollector, PatternPersistence, StateManager
    from .trust_building import TrustBuildingBehaviors

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
    # coordination
    "AgentCoordinator": (".coordination", "AgentCoordinator"),
    "AgentTask": (".coordination", "AgentTask"),
    "ConflictResolver": (".coordination", "ConflictResolver"),
    "ResolutionResult": (".coordination", "ResolutionResult"),
    "ResolutionStrategy": (".coordination", "ResolutionStrategy"),
    "TeamPriorities": (".coordination", "TeamPriorities"),
    "TeamSession": (".coordination", "TeamSession"),
    # core
    "EmpathyOS": (".core", "EmpathyOS"),
    # emergence
    "EmergenceDetector": (".emergence", "EmergenceDetector"),
    # exceptions
    "CollaborationStateError": (".exceptions", "CollaborationStateError"),
    "ConfidenceThresholdError": (".exceptions", "ConfidenceThresholdError"),
    "EmpathyFrameworkError": (".exceptions", "EmpathyFrameworkError"),
    "EmpathyLevelError": (".exceptions", "EmpathyLevelError"),
    "FeedbackLoopError": (".exceptions", "FeedbackLoopError"),
    "LeveragePointError": (".exceptions", "LeveragePointError"),
    "PatternNotFoundError": (".exceptions", "PatternNotFoundError"),
    "TrustThresholdError": (".exceptions", "TrustThresholdError"),
    "ValidationError": (".exceptions", "ValidationError"),
    # feedback_loops
    "FeedbackLoopDetector": (".feedback_loops", "FeedbackLoopDetector"),
    # levels
    "Level1Reactive": (".levels", "Level1Reactive"),
    "Level2Guided": (".levels", "Level2Guided"),
    "Level3Proactive": (".levels", "Level3Proactive"),
    "Level4Anticipatory": (".levels", "Level4Anticipatory"),
    "Level5Systems": (".levels", "Level5Systems"),
    # leverage_points
    "LeveragePointAnalyzer": (".leverage_points", "LeveragePointAnalyzer"),
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
    # trust_building
    "TrustBuildingBehaviors": (".trust_building", "TrustBuildingBehaviors"),
}

# Cache for loaded modules
_loaded_modules: dict[str, object] = {}


def __getattr__(name: str) -> object:
    """Lazy import handler - loads modules only when accessed."""
    if name in _LAZY_IMPORTS:
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
    "AgentCoordinator",
    "AgentCredentials",
    "AgentMetrics",
    # Monitoring (Multi-Agent)
    "AgentMonitor",
    "AgentTask",
    "AuditEvent",
    # Security - Audit
    "AuditLogger",
    "Classification",
    "ClassificationRules",
    # Claude Memory
    "ClaudeMemoryConfig",
    "ClaudeMemoryLoader",
    "CollaborationStateError",
    "ConfidenceThresholdError",
    "ConflictContext",
    # Coordination (Multi-Agent)
    "ConflictResolver",
    "EmergenceDetector",
    # Configuration
    "AttuneConfig",
    "EmpathyConfig",
    # Exceptions
    "EmpathyFrameworkError",
    "EmpathyLevelError",
    "EmpathyOS",
    "EncryptionManager",
    "Environment",
    "FeedbackLoopDetector",
    "FeedbackLoopError",
    "Level1Reactive",
    "Level2Guided",
    "Level3Proactive",
    "Level4Anticipatory",
    "Level5Systems",
    "LeveragePointAnalyzer",
    "LeveragePointError",
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
    "PatternNotFoundError",
    # Persistence
    "PatternPersistence",
    # Redis Short-Term Memory
    "RedisShortTermMemory",
    "ResolutionResult",
    "ResolutionStrategy",
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
    "TeamPriorities",
    "TeamSession",
    # Trust
    "TrustBuildingBehaviors",
    "TrustThresholdError",
    # Unified Memory Interface
    "UnifiedMemory",
    "ValidationError",
    "check_redis_connection",
    "detect_secrets",
    # Logging
    "get_logger",
    "get_railway_redis",
    "get_redis_config",
    # Redis Configuration
    "get_redis_memory",
    "load_config",
]
