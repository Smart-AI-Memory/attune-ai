---
type: reference
feature: models
depth: reference
generated_at: 2026-04-14T15:13:38.281363+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models reference

## Classes

### ModelPerformance

Performance metrics for a model on a specific task.

| Field | Type | Default |
|-------|------|---------|
| `model_id` | `str` | - |
| `tier` | `str` | - |
| `success_rate` | `float` | - |
| `avg_latency_ms` | `float` | - |
| `avg_cost` | `float` | - |
| `sample_size` | `int` | - |
| `recent_failures` | `int` | `0` |

| Property | Type | Description |
|----------|------|-------------|
| `quality_score` | `float` | Calculate quality score for ranking models |

### AdaptiveModelRouter

Route tasks to models based on historical telemetry performance.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `telemetry: Any` | - | Initialize router with telemetry |
| `get_best_model` | `workflow: str, stage: str, max_cost: float | None = None, max_latency_ms: int | None = None, min_success_rate: float = 0.8` | `str` | Get best model for task |
| `recommend_tier_upgrade` | `workflow: str, stage: str` | `tuple[bool, str]` | Recommend tier upgrade |
| `get_routing_stats` | `workflow: str, stage: str | None = None, days: int = 7` | `dict[str, Any]` | Get routing statistics |

### AuthStrategy

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

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_recommended_mode` | `module_lines: int` | `AuthMode` | Get recommended authentication mode |
| `estimate_tokens` | `module_lines: int` | `int` | Estimate token count |
| `estimate_cost` | `module_lines: int, mode: AuthMode | None = None` | `dict[str, Any]` | Estimate cost |
| `get_pros_cons` | `module_lines: int` | `dict[str, Any]` | Get pros and cons |
| `to_dict` | - | `dict[str, Any]` | Convert to dictionary |
| `from_dict` | `data: dict[str, Any]` | `AuthStrategy` | Create from dictionary |
| `save` | `path: Path | None = None` | `None` | Save to file |
| `load` | `path: Path | None = None` | `AuthStrategy` | Load from file |

### CircuitBreakerState

State of a circuit breaker for a provider.

| Field | Type | Default |
|-------|------|---------|
| `failure_count` | `int` | `0` |
| `last_failure` | `datetime | None` | `None` |
| `is_open` | `bool` | `False` |
| `opened_at` | `datetime | None` | `None` |

### CircuitBreaker

Circuit breaker to temporarily disable failing providers.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `failure_threshold: int = 5, recovery_timeout_seconds: int = 60, half_open_calls: int = 1` | - | Initialize circuit breaker |
| `is_available` | `provider: str, tier: str | None = None` | `bool` | Check if provider is available |
| `record_success` | `provider: str, tier: str | None = None` | `None` | Record successful call |
| `record_failure` | `provider: str, tier: str | None = None` | `None` | Record failed call |
| `get_status` | - | `dict[str, dict[str, Any]]` | Get status of all providers |
| `reset` | `provider: str | None = None, tier: str | None = None` | `None` | Reset circuit breaker |

### EmpathyLLMExecutor

Default executor wrapping EmpathyLLM with routing.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `empathy_llm: Any | None = None, provider: str = 'anthropic', api_key: str | None = None, telemetry_store: TelemetryBackend | TelemetryStore | None = None, use_thinking: bool = False, thinking_budget: int = 10000, **llm_kwargs: Any` | - | Initialize executor |
| `run` | `task_type: str, prompt: str, system: str | None = None, context: ExecutionContext | None = None, **kwargs: Any` | `LLMResponse` | Execute LLM task |
| `get_model_for_task` | `task_type: str` | `str` | Get model for task type |
| `estimate_cost` | `task_type: str, input_tokens: int, output_tokens: int` | `float` | Estimate execution cost |

### LLMResponse

Standardized response from an LLM execution.

| Field | Type | Default |
|-------|------|---------|
| `content` | `str` | - |
| `model_id` | `str` | - |
| `provider` | `str` | - |
| `tier` | `str` | - |
| `tokens_input` | `int` | `0` |
| `tokens_output` | `int` | `0` |
| `cost_estimate` | `float` | `0.0` |
| `latency_ms` | `int` | `0` |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

| Property | Type | Description |
|----------|------|-------------|
| `input_tokens` | `int` | Alias for tokens_input (backwards compatibility) |
| `output_tokens` | `int` | Alias for tokens_output (backwards compatibility) |
| `model_used` | `str` | Alias for model_id (backwards compatibility) |
| `cost` | `float` | Alias for cost_estimate (backwards compatibility) |
| `total_tokens` | `int` | Total tokens used (input + output) |
| `success` | `bool` | Check if the response was successful (has content) |

### ExecutionContext

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

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_auth_setup` | `args: Any` | `int` | Run interactive authentication strategy setup |
| `cmd_auth_status` | `args: Any` | `int` | Show current authentication strategy configuration |
| `cmd_auth_reset` | `args: Any` | `int` | Reset/clear authentication strategy configuration |
| `cmd_auth_recommend` | `args: Any` | `int` | Get authentication recommendation for a specific file |
| `main` | - | `int` | Main CLI entry point |
| `configure_auth_interactive` | `module_lines: int = 1000` | `AuthStrategy` | Interactive authentication configuration (first-time setup) |
| `get_auth_strategy` | - | `AuthStrategy` | Get the global authentication strategy |
| `count_lines_of_code` | `file_path: str | Path` | `int` | Count lines of code in a Python file |
| `get_module_size_category` | `module_lines: int` | `str` | Categorize module size |
| `print_registry` | `provider: str | None = None, format: str = 'table'` | `None` | Print the model registry |

### CLI main return values

The `main` function returns:

```
1
```

### get_module_size_category return values

The `get_module_size_category` function returns:

```
'large'
```

## Constants

| Constant | Values |
|----------|--------|
| `REALTIME_REQUIRED_TASKS` | `{'chat', 'interactive_debug', 'live_coding', 'user_query', 'workflow_step', 'critical_fix', 'security_incident', 'emergency_response', 'stream_analysis', 'realtime_monitoring'}` |
