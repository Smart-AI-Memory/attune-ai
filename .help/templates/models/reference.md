---
type: reference
name: models-reference
feature: models
depth: reference
generated_at: 2026-05-16T06:19:45.834928+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models reference

Configure authentication, route tasks to LLM providers, and manage model tiers.

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
| `ModelInfo` | Unified model information — single source of truth. | `src/attune/models/registry.py` |
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

### `ModelPerformance` fields

| Field | Type | Default |
|-------|------|---------|
| `model_id` | `str` | — |
| `tier` | `str` | — |
| `success_rate` | `float` | — |
| `avg_latency_ms` | `float` | — |
| `avg_cost` | `float` | — |
| `sample_size` | `int` | — |
| `recent_failures` | `int` | `0` |

#### `ModelPerformance` properties

| Property | Type | Description |
|----------|------|-------------|
| `quality_score` | `float` | Calculate quality score for ranking models. |

### `AdaptiveModelRouter` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `telemetry: Any` | — | Initialize the router with a telemetry source. |
| `get_best_model` | `workflow: str, stage: str, max_cost: float | None = None, max_latency_ms: int | None = None, min_success_rate: float = 0.8` | `str` | Return the best model for a workflow stage based on telemetry. |
| `recommend_tier_upgrade` | `workflow: str, stage: str` | `tuple[bool, str]` | Recommend whether a tier upgrade is warranted for a workflow stage. |
| `get_routing_stats` | `workflow: str, stage: str | None = None, days: int = 7` | `dict[str, Any]` | Return routing statistics for a workflow stage over a time window. |

### `AuthStrategy` fields

| Field | Type | Default |
|-------|------|---------|
| `subscription_tier` | `SubscriptionTier` | `SubscriptionTier.PRO` |
| `default_mode` | `AuthMode` | `AuthMode.AUTO` |
| `small_module_threshold` | `int` | `500` |
| `medium_module_threshold` | `int` | `2000` |
| `loc_to_tokens_multiplier` | `float` | `4.0` |
| `setup_completed` | `bool` | `True` |
| `prefer_subscription` | `bool` | `True` |
| `cost_optimization` | `bool` | `True` |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

#### `AuthStrategy` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_recommended_mode` | `module_lines: int` | `AuthMode` | Return the recommended authentication mode for a module of the given size. |
| `estimate_tokens` | `module_lines: int` | `int` | Estimate token usage for a module of the given size. |
| `estimate_cost` | `module_lines: int, mode: AuthMode | None = None` | `dict[str, Any]` | Estimate cost for a module, optionally scoped to a specific auth mode. |
| `get_pros_cons` | `module_lines: int` | `dict[str, Any]` | Return pros and cons for each auth mode given the module size. |
| `to_dict` | — | `dict[str, Any]` | Serialize the strategy to a dictionary. |
| `from_dict` | `data: dict[str, Any]` | `AuthStrategy` | Deserialize a strategy from a dictionary. |
| `save` | `path: Path | None = None` | `None` | Save the strategy to disk. |
| `load` | `path: Path | None = None` | `AuthStrategy` | Load the strategy from disk. |

### `CircuitBreakerState` fields

| Field | Type | Default |
|-------|------|---------|
| `failure_count` | `int` | `0` |
| `last_failure` | `datetime | None` | `None` |
| `is_open` | `bool` | `False` |
| `opened_at` | `datetime | None` | `None` |

### `CircuitBreaker` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `failure_threshold: int = 5, recovery_timeout_seconds: int = 60, half_open_calls: int = 1` | — | Initialize the circuit breaker with failure and recovery thresholds. |
| `is_available` | `provider: str, tier: str | None = None` | `bool` | Check whether a provider is currently available. |
| `record_success` | `provider: str, tier: str | None = None` | `None` | Record a successful call to a provider. |
| `record_failure` | `provider: str, tier: str | None = None` | `None` | Record a failed call to a provider. |
| `get_status` | — | `dict[str, dict[str, Any]]` | Return the current status of all tracked providers. |
| `reset` | `provider: str | None = None, tier: str | None = None` | `None` | Reset circuit breaker state for a provider or all providers. |

### `EmpathyLLMExecutor` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `empathy_llm: Any | None = None, provider: str = 'anthropic', api_key: str | None = None, telemetry_store: TelemetryBackend | TelemetryStore | None = None, use_thinking: bool = False, thinking_budget: int = 10000, **llm_kwargs: Any` | — | Initialize the executor with an optional EmpathyLLM instance and routing config. |
| `run` | `task_type: str, prompt: str, system: str | None = None, context: ExecutionContext | None = None, **kwargs: Any` | `LLMResponse` | Execute a prompt for the given task type and return a standardized response. |
| `get_model_for_task` | `task_type: str` | `str` | Return the model ID selected for a task type. |
| `estimate_cost` | `task_type: str, input_tokens: int, output_tokens: int` | `float` | Estimate the cost of an LLM call in USD. |

### `LLMResponse` fields

| Field | Type | Default |
|-------|------|---------|
| `content` | `str` | — |
| `model_id` | `str` | — |
| `provider` | `str` | — |
| `tier` | `str` | — |
| `tokens_input` | `int` | `0` |
| `tokens_output` | `int` | `0` |
| `cost_estimate` | `float` | `0.0` |
| `latency_ms` | `int` | `0` |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

#### `LLMResponse` properties

| Property | Type | Description |
|----------|------|-------------|
| `input_tokens` | `int` | Alias for `tokens_input` (backwards compatibility). |
| `output_tokens` | `int` | Alias for `tokens_output` (backwards compatibility). |
| `model_used` | `str` | Alias for `model_id` (backwards compatibility). |
| `cost` | `float` | Alias for `cost_estimate` (backwards compatibility). |
| `total_tokens` | `int` | Total tokens used (input + output). |
| `success` | `bool` | `True` if the response contains content. |

### `ExecutionContext` fields

| Field | Type | Default |
|-------|------|---------|
| `user_id` | `str | None` | `None` |
| `workflow_name` | `str | None` | `None` |
| `step_name` | `str | None` | `None` |
| `task_type` | `str | None` | `None` |
| `provider_hint` | `str | None` | `None` |
| `tier_hint` | `str | None` | `None` |
| `timeout_seconds` | `int | None` | `None` |
| `session_id` | `str | None` | `None` |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `cmd_auth_setup` | `args: Any` | `int` | Run interactive authentication strategy setup. | `src/attune/models/auth_cli.py` |
| `cmd_auth_status` | `args: Any` | `int` | Show current authentication strategy configuration. | `src/attune/models/auth_cli.py` |
| `cmd_auth_reset` | `args: Any` | `int` | Reset/clear authentication strategy configuration. | `src/attune/models/auth_cli.py` |
| `cmd_auth_recommend` | `args: Any` | `int` | Get authentication recommendation for a specific file. | `src/attune/models/auth_cli.py` |
| `main` | — | `int` | Main CLI entry point. | `src/attune/models/auth_cli.py` |
| `configure_auth_interactive` | `module_lines: int = 1000` | `AuthStrategy` | Interactive authentication configuration (first-time setup). | `src/attune/models/auth_strategy.py` |
| `get_auth_strategy` | — | `AuthStrategy` | Get the global authentication strategy. | `src/attune/models/auth_strategy.py` |
| `count_lines_of_code` | `file_path: str | Path` | `int` | Count lines of code in a Python file. | `src/attune/models/auth_strategy.py` |
| `get_module_size_category` | `module_lines: int` | `str` | Categorize module size. | `src/attune/models/auth_strategy.py` |
| `print_registry` | `provider: str | None = None, format: str = 'table'` | `None` | Print the model registry. | `src/attune/models/cli.py` |
| `print_tasks` | `tier: str | None = None, format: str = 'table'` | `None` | Print task-to-tier mappings. | `src/attune/models/cli.py` |
| `print_costs` | `input_tokens: int = 10000, output_tokens: int = 2000, provider:
