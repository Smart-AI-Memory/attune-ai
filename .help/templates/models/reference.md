---
feature: models
depth: reference
generated_at: 2026-04-06T04:33:52.122736+00:00
source_hash: 5281a9cce870400fa1f93a29dd9b940cdc17f1029494b1b3ceec79cbe9969f3c
status: generated
---

# Models reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ModelPerformance` | Performance metrics for a model on a specific task. | `src/attune/models/adaptive_routing.py` |
| `AdaptiveModelRouter` | Route tasks to models based on historical telemetry performance. | `src/attune/models/adaptive_routing.py` |
| `SubscriptionTier` | Claude subscription tiers. | `src/attune/models/auth_strategy.py` |
| `AuthMode` | Authentication mode selection. | `src/attune/models/auth_strategy.py` |
| `AuthStrategy` | Authentication strategy configuration. | `src/attune/models/auth_strategy.py` |
| `CircuitBreakerState` | State of a circuit breaker for a provider. | `src/attune/models/circuit_breaker.py` |
| `CircuitBreaker` | Circuit breaker to temporarily disable failing providers. | `src/attune/models/circuit_breaker.py` |
| `EmpathyLLMExecutor` | Default executor wrapping EmpathyLLM with routing. | `src/attune/models/empathy_executor.py` |
| `LLMResponse` | Standardized response from an LLM execution. | `src/attune/models/executor.py` |
| `ExecutionContext` | Context for an LLM execution. | `src/attune/models/executor.py` |
| `LLMExecutor` | Protocol for unified LLM execution across routing and workflows. | `src/attune/models/executor.py` |
| `MockLLMExecutor` | Mock executor for testing. | `src/attune/models/executor.py` |
| `FallbackStrategy` | Strategies for selecting fallback models. | `src/attune/models/fallback_policy.py` |
| `FallbackStep` | A single step in a fallback chain. | `src/attune/models/fallback_policy.py` |
| `FallbackPolicy` | Policy for handling LLM failures with fallback chains. | `src/attune/models/fallback_policy.py` |
| `ProviderMode` | Provider selection mode (Anthropic-only as of v5.0.0). | `src/attune/models/provider_config.py` |
| `ProviderConfig` | User's provider configuration. | `src/attune/models/provider_config.py` |
| `ModelTier` | Model tier classification for routing. | `src/attune/models/registry.py` |
| `ModelProvider` | Supported model provider (Claude-native architecture as of v3.0.0). | `src/attune/models/registry.py` |
| `ModelInfo` | Unified model information - single source of truth. | `src/attune/models/registry.py` |
| `ModelRegistry` | Object-oriented interface to the model registry. | `src/attune/models/registry.py` |
| `AllProvidersFailedError` | Raised when all fallback providers have failed. | `src/attune/models/resilient_executor.py` |
| `ResilientExecutor` | Wrapper that adds resilience to LLM execution. | `src/attune/models/resilient_executor.py` |
| `RetryPolicy` | Policy for retrying failed LLM calls. | `src/attune/models/retry.py` |
| `TaskType` | Canonical task types for model routing. | `src/attune/models/tasks.py` |
| `TaskInfo` | Information about a task type. | `src/attune/models/tasks.py` |
| `TelemetryAnalytics` | Analytics helpers for telemetry data. | `src/attune/models/telemetry/analytics.py` |
| `TelemetryBackend` | Protocol for telemetry storage backends. | `src/attune/models/telemetry/backend.py` |
| `LLMCallRecord` | Record of a single LLM API call. | `src/attune/models/telemetry/data_models.py` |
| `WorkflowStageRecord` | Record of a single workflow stage execution. | `src/attune/models/telemetry/data_models.py` |
| `WorkflowRunRecord` | Record of a complete workflow execution. | `src/attune/models/telemetry/data_models.py` |
| `TaskRoutingRecord` | Record of task routing decision for Tier 1 automation. | `src/attune/models/telemetry/data_models.py` |
| `TestExecutionRecord` | Record of test execution for Tier 1 QA automation. | `src/attune/models/telemetry/data_models.py` |
| `CoverageRecord` | Record of test coverage metrics for Tier 1 QA monitoring. | `src/attune/models/telemetry/data_models.py` |
| `AgentAssignmentRecord` | Record of agent assignment for simple tasks (Tier 1). | `src/attune/models/telemetry/data_models.py` |
| `FileTestRecord` | Record of test execution for a specific source file. | `src/attune/models/telemetry/data_models.py` |
| `TelemetryStore` | JSONL file-based telemetry backend (default implementation). | `src/attune/models/telemetry/storage.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `cmd_auth_setup()` | Run interactive authentication strategy setup. | `src/attune/models/auth_cli.py` |
| `cmd_auth_status()` | Show current authentication strategy configuration. | `src/attune/models/auth_cli.py` |
| `cmd_auth_reset()` | Reset/clear authentication strategy configuration. | `src/attune/models/auth_cli.py` |
| `cmd_auth_recommend()` | Get authentication recommendation for a specific file. | `src/attune/models/auth_cli.py` |
| `main()` | Main CLI entry point. | `src/attune/models/auth_cli.py` |
| `configure_auth_interactive()` | Interactive authentication configuration (first-time setup). | `src/attune/models/auth_strategy.py` |
| `get_auth_strategy()` | Get the global authentication strategy. | `src/attune/models/auth_strategy.py` |
| `count_lines_of_code()` | Count lines of code in a Python file. | `src/attune/models/auth_strategy.py` |
| `get_module_size_category()` | Categorize module size. | `src/attune/models/auth_strategy.py` |
| `print_registry()` | Print the model registry. | `src/attune/models/cli.py` |
| `print_tasks()` | Print task-to-tier mappings. | `src/attune/models/cli.py` |
| `print_costs()` | Print cost estimates for all tiers. | `src/attune/models/cli.py` |
| `print_effective_config()` | Print the effective configuration for a provider. | `src/attune/models/cli.py` |
| `print_telemetry_summary()` | Print telemetry summary. | `src/attune/models/cli.py` |
| `print_telemetry_costs()` | Print cost savings report. | `src/attune/models/cli.py` |
| `print_telemetry_providers()` | Print provider usage summary. | `src/attune/models/cli.py` |
| `print_telemetry_fallbacks()` | Print fallback statistics. | `src/attune/models/cli.py` |
| `print_provider_config()` | Print current provider configuration. | `src/attune/models/cli.py` |
| `configure_provider()` | Configure provider settings. | `src/attune/models/cli.py` |
| `main()` | Main CLI entry point. | `src/attune/models/cli.py` |
| `configure_provider_interactive()` | Interactive provider configuration for install/update (Anthropic-only as of v5.0.0). | `src/attune/models/provider_config.py` |
| `configure_provider_cli()` | CLI-based provider configuration (Anthropic-only as of v5.0.0). | `src/attune/models/provider_config.py` |
| `get_provider_config()` | Get the global provider configuration. | `src/attune/models/provider_config.py` |
| `set_provider_config()` | Set the global provider configuration. | `src/attune/models/provider_config.py` |
| `reset_provider_config()` | Reset the global provider configuration (forces reload). | `src/attune/models/provider_config.py` |
| `configure_hybrid_interactive()` | Interactive hybrid provider configuration (DEPRECATED in v5.0.0). | `src/attune/models/provider_config.py` |
| `get_model()` | Get model info for a provider/tier combination. | `src/attune/models/registry.py` |
| `get_all_models()` | Get the complete model registry. | `src/attune/models/registry.py` |
| `get_pricing_for_model()` | Get pricing for a model by its ID. | `src/attune/models/registry.py` |
| `get_supported_providers()` | Get list of supported provider names. | `src/attune/models/registry.py` |
| `get_tiers()` | Get list of available tiers. | `src/attune/models/registry.py` |
| `normalize_task_type()` | Normalize a task type string for lookup. | `src/attune/models/tasks.py` |
| `get_tier_for_task()` | Get the appropriate tier for a task type. | `src/attune/models/tasks.py` |
| `get_tasks_for_tier()` | Get all task types for a given tier. | `src/attune/models/tasks.py` |
| `get_all_tasks()` | Get all known task types organized by tier. | `src/attune/models/tasks.py` |
| `is_known_task()` | Check if a task type is known/defined. | `src/attune/models/tasks.py` |
| `get_telemetry_store()` | Get singleton telemetry store instance. | `src/attune/models/telemetry/__init__.py` |
| `log_llm_call()` | Log an LLM API call. | `src/attune/models/telemetry/__init__.py` |
| `log_workflow_run()` | Log a workflow run. | `src/attune/models/telemetry/__init__.py` |
| `estimate_tokens()` | Estimate token count for text using accurate token counting. | `src/attune/models/token_estimator.py` |
| `estimate_workflow_cost()` | Estimate total workflow cost before execution. | `src/attune/models/token_estimator.py` |
| `estimate_single_call_cost()` | Estimate cost for a single LLM call. | `src/attune/models/token_estimator.py` |


## Source files

- `src/attune/models/**`

## Tags

`models`, `auth`, `llm`
