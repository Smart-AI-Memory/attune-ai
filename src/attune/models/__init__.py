"""Unified Model Registry for Attune AI

Single source of truth for model configurations across:
- attune.routing.ModelRouter
- src/attune/workflows.WorkflowConfig
- src/attune.cost_tracker

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .adaptive_routing import AdaptiveModelRouter, ModelPerformance
from .auth_strategy import (
    AUTH_STRATEGY_FILE,
    AuthMode,
    AuthStrategy,
    SubscriptionTier,
    configure_auth_interactive,
    count_lines_of_code,
    get_auth_strategy,
    get_module_size_category,
)
from .empathy_executor import EmpathyLLMExecutor
from .executor import ExecutionContext, LLMExecutor, LLMResponse, MockLLMExecutor
from .fallback import (
    DEFAULT_FALLBACK_POLICY,
    DEFAULT_RETRY_POLICY,
    CircuitBreaker,
    CircuitBreakerState,
    FallbackPolicy,
    FallbackStep,
    FallbackStrategy,
    ResilientExecutor,
    RetryPolicy,
)
from .provider_config import (
    ProviderConfig,
    ProviderMode,
    configure_provider_cli,
    configure_provider_interactive,
    get_provider_config,
    reset_provider_config,
    set_provider_config,
)
from .registry import (
    MODEL_REGISTRY,
    ModelInfo,
    ModelProvider,
    ModelRegistry,
    ModelTier,
    get_all_models,
    get_model,
    get_pricing_for_model,
)
from .tasks import (
    CAPABLE_TASKS,
    CHEAP_TASKS,
    PREMIUM_TASKS,
    TASK_TIER_MAP,
    TaskInfo,
    TaskType,
    get_all_tasks,
    get_tasks_for_tier,
    get_tier_for_task,
    is_known_task,
    normalize_task_type,
)
from .telemetry import (
    AgentAssignmentRecord,
    CoverageRecord,
    DiagnosisRecord,
    FileTestRecord,
    LLMCallRecord,
    TaskRoutingRecord,
    TelemetryAnalytics,
    TelemetryBackend,
    TelemetryStore,
    TestExecutionRecord,
    WorkflowRunRecord,
    WorkflowStageRecord,
    get_telemetry_store,
    log_llm_call,
    log_workflow_run,
)

__all__ = [
    "CAPABLE_TASKS",
    "CHEAP_TASKS",
    "DEFAULT_FALLBACK_POLICY",
    "DEFAULT_RETRY_POLICY",
    "MODEL_REGISTRY",
    "PREMIUM_TASKS",
    "TASK_TIER_MAP",
    "AdaptiveModelRouter",
    "AgentAssignmentRecord",
    # Auth strategy exports
    "AUTH_STRATEGY_FILE",
    "AuthMode",
    "AuthStrategy",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CoverageRecord",
    "DiagnosisRecord",
    "EmpathyLLMExecutor",
    "ExecutionContext",
    "FallbackPolicy",
    "FallbackStep",
    # Fallback exports
    "FallbackStrategy",
    # Telemetry exports
    "FileTestRecord",
    "LLMCallRecord",
    # Executor exports
    "LLMExecutor",
    "LLMResponse",
    "MockLLMExecutor",
    "ModelInfo",
    "ModelPerformance",
    "ModelProvider",
    # Registry exports
    "ModelRegistry",
    "ModelTier",
    "ProviderConfig",
    # Provider config exports
    "ProviderMode",
    "ResilientExecutor",
    "RetryPolicy",
    "SubscriptionTier",
    "TaskInfo",
    # Task exports
    "TaskRoutingRecord",
    "TaskType",
    "TelemetryAnalytics",
    "TelemetryBackend",
    "TelemetryStore",
    "TestExecutionRecord",
    "WorkflowRunRecord",
    "WorkflowStageRecord",
    "configure_auth_interactive",
    "configure_provider_cli",
    "configure_provider_interactive",
    "count_lines_of_code",
    "get_all_models",
    "get_all_tasks",
    "get_auth_strategy",
    "get_model",
    "get_module_size_category",
    "get_pricing_for_model",
    "get_provider_config",
    "get_tasks_for_tier",
    "get_telemetry_store",
    "get_tier_for_task",
    "is_known_task",
    "log_llm_call",
    "log_workflow_run",
    "normalize_task_type",
    "reset_provider_config",
    "set_provider_config",
]
