---
type: reference
name: models-reference
feature: models
depth: reference
generated_at: 2026-06-04T23:45:26.749578+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models reference

APIs for LLM authentication, provider routing, tier management, and telemetry in Attune AI.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ModelPerformance` | Performance metrics for a model on a specific task. | `src/attune/models/adaptive_routing.py` |
| `AdaptiveModelRouter` | Routes tasks to models based on historical telemetry performance. | `src/attune/models/adaptive_routing.py` |
| `SubscriptionTier` | Claude subscription tiers. | `src/attune/models/auth_strategy.py` |
| `AuthMode` | Authentication mode selection. | `src/attune/models/auth_strategy.py` |
| `AuthStrategy` | Authentication strategy configuration. | `src/attune/models/auth_strategy.py` |
| `CircuitBreakerState` | State of a circuit breaker for a provider. | `src/attune/models/circuit_breaker.py` |
| `CircuitBreaker` | Temporarily disables failing providers. | `src/attune/models/circuit_breaker.py` |
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
| `ModelInfo` | Unified model information — single source of truth for the model registry. | `src/attune/models/registry.py` |
| `ModelRegistry` | Object-oriented interface to the model registry. | `src/attune/models/registry.py` |
| `AllProvidersFailedError` | Raised when all fallback providers have failed. | `src/attune/models/resilient_executor.py` |
| `ResilientExecutor` | Adds resilience (retry and fallback) to LLM execution. | `src/attune/models/resilient_executor.py` |
| `RetryPolicy` | Policy for retrying failed LLM calls. | `src/attune/models/retry.py` |
| `TaskType` | Canonical task types for model routing. | `src/attune/models/tasks.py` |
| `TaskInfo` | Information about a task type. | `src/attune/models/tasks.py` |
| `TelemetryAnalytics` | Analytics helpers for telemetry data. | `src/attune/models/telemetry/analytics.py` |
| `TelemetryBackend` | Protocol for telemetry storage backends. | `src/attune/models/telemetry/backend.py` |
| `LLMCallRecord` | Record of a single LLM API call. | `src/attune/models/telemetry/data_models.py` |
| `WorkflowStageRecord` | Record of a single workflow stage execution. | `src/attune/models/telemetry/data_models.py` |
| `WorkflowRunRecord` | Record of a complete workflow execution. | `src/attune/models/telemetry/data_models.py` |
| `TaskRoutingRecord` | Record of a task routing decision for Tier 1 automation. | `src/attune/models/telemetry/data_models.py` |
| `TestExecutionRecord` | Record of a test execution for Tier 1 QA automation. | `src/attune/models/telemetry/data_models.py` |
| `CoverageRecord` | Record of test coverage metrics for Tier 1 QA monitoring. | `src/attune/models/telemetry/data_models.py` |
| `AgentAssignmentRecord` | Record of an agent assignment for simple tasks (Tier 1). | `src/attune/models/telemetry/data_models.py` |
| `FileTestRecord` | Record of test execution for a specific source file. | `src/attune/models/telemetry/data_models.py` |
| `TelemetryStore` | JSONL file-based telemetry backend (default implementation). | `src/attune/models/telemetry/storage.py` |

## Dataclass fields

### `ModelPerformance`

Performance metrics for a model on a specific task.

| Field | Type | Default |
|-------|------|---------|
| `model_id` | `str` | — |
| `tier` | `str` | — |
| `success_rate` | `float` | — |
| `avg_latency_ms` | `float` | — |
| `avg_cost` | `float` | — |
| `sample_size` | `int` | — |
| `recent_failures` | `int` | `0` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `quality_score` | `float` | Calculates quality score for ranking models. |

---

### `AuthStrategy`

Authentication strategy configuration.

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

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_recommended_mode` | `module_lines: int` | `AuthMode` | Returns the recommended auth mode for a module of the given size. |
| `estimate_tokens` | `module_lines: int` | `int` | Estimates token count for a module of the given size. |
| `estimate_cost` | `module_lines: int, mode: AuthMode | None = None` | `dict[str, Any]` | Estimates cost for processing a module in the given mode. |
| `get_pros_cons` | `module_lines: int` | `dict[str, Any]` | Returns pros and cons for each auth mode given the module size. |
| `to_dict` | — | `dict[str, Any]` | Serializes the strategy to a dictionary. |
| `from_dict` | `data: dict[str, Any]` | `AuthStrategy` | Deserializes a strategy from a dictionary. |
| `save` | `path: Path | None = None` | `None` | Saves the strategy to disk. |
| `load` | `path: Path | None = None` | `AuthStrategy` | Loads the strategy from disk. |

---

### `CircuitBreakerState`

State of a circuit breaker for a provider.

| Field | Type | Default |
|-------|------|---------|
| `failure_count` | `int` | `0` |
| `last_failure` | `datetime | None` | `None` |
| `is_open` | `bool` | `False` |
| `opened_at` | `datetime | None` | `None` |

---

### `LLMResponse`

Standardized response from an LLM execution.

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

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `input_tokens` | `int` | Alias for `tokens_input` (backwards compatibility). |
| `output_tokens` | `int` | Alias for `tokens_output` (backwards compatibility). |
| `model_used` | `str` | Alias for `model_id` (backwards compatibility). |
| `cost` | `float` | Alias for `cost_estimate` (backwards compatibility). |
| `total_tokens` | `int` | Total tokens used (input + output). |
| `success` | `bool` | `True` if the response has content. |

---

### `ExecutionContext`

Context for an LLM execution.

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

## Class methods

### `AdaptiveModelRouter`

Routes tasks to models based on historical telemetry performance.

**Constructor:** `__init__(self, telemetry: Any)`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_best_model` | `workflow: str, stage: str, max_cost: float | None = None, max_latency_ms: int | None = None, min_success_rate: float = 0.8` | `str` | Returns the best model ID for a workflow stage given cost, latency, and success-rate constraints. |
| `recommend_tier_upgrade` | `workflow: str, stage: str` | `tuple[bool, str]` | Returns whether a tier upgrade is recommended for a workflow stage, and the reason. |
| `get_routing_stats` | `workflow: str, stage: str | None = None, days: int = 7` | `dict[str, Any]` | Returns routing statistics for a workflow over the given number of days. |

---

### `CircuitBreaker`

Temporarily disables failing providers to prevent cascading failures.

**Constructor:** `__init__(self, failure_threshold: int = 5, recovery_timeout_seconds: int = 60, half_open_calls: int = 1)`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `is_available` | `provider: str, tier: str | None = None` | `bool` | Returns whether a provider (and optional tier) is currently available. |
| `record_success` | `provider: str, tier: str | None = None` | `None` | Records a successful call for a provider. |
| `record_failure` | `provider: str, tier: str | None = None` | `None` | Records a failed call for a provider. |
| `get_status` | — | `dict[str, dict[str, Any]]` | Returns the current circuit breaker status for all providers. |
| `reset` | `provider: str | None = None, tier: str | None = None` | `None` | Resets the circuit breaker for a provider or all providers. |

---

### `EmpathyLLMExecutor`

Default executor wrapping EmpathyLLM with routing.

**Constructor:** `__init__(self, empathy_llm: Any | None = None, provider: str = 'anthropic', api_key: str | None = None, telemetry_store: TelemetryBackend | TelemetryStore | None = None, use_thinking: bool = False, thinking_budget: int = 10000, **llm_kwargs: Any)`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run` | `task_type: str, prompt: str, system: str | None = None, context: ExecutionContext | None = None, **kwargs: Any` | `LLMResponse` | Executes an LLM call for the given task type and prompt. |
| `get_model_for_task` | `task_type: str` | `str` | Returns the model ID selected for a given task type. |
| `estimate_cost` | `task_type: str, input_tokens: int, output_tokens: int` | `float` | Estimates the cost for a task given token counts. |

## Functions

### Authentication (`src/attune/models/auth_cli.py`, `src/attune/models/auth_strategy.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_auth_setup` | `args: Any` | `int` | Runs interactive authentication strategy setup. |
| `cmd_auth_status` | `args: Any` | `int` | Shows the current authentication strategy configuration. |
| `cmd_auth_reset` | `args: Any` | `int` | Resets the authentication strategy configuration. |
| `cmd_auth_recommend` | `args: Any` | `int` | Gets an authentication recommendation for a specific file. |
| `main` | — | `int` | Main CLI entry point for `auth_cli`. |
| `configure_auth_interactive` | `module_lines: int = 1000` | `AuthStrategy` | Runs first-time interactive authentication configuration. |
| `get_auth_strategy` | — | `AuthStrategy` | Returns the global authentication strategy. |
| `count_lines_of_code` | `file_path: str | Path` | `int` | Counts lines of code in a Python file. |
| `get_module_size_category` | `module_lines: int` | `str` | Categorizes a module by size (e.g., `'large'`). |

### Registry and providers (`src/attune/models/registry.py`, `src/attune/models/provider_config.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_model` | `provider: str, tier: str` | `ModelInfo | None` | Returns model info for a provider/tier combination. |
| `get_all_models` | — | `dict[str, dict[str, ModelInfo]]` | Returns the complete model registry. |
| `get_pricing_for_model` | `model_id: str` |
