---
type: reference
feature: models
depth: reference
generated_at: 2026-05-04T02:35:06.105588+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models reference

Route LLM tasks, manage authentication, and track performance across model providers.

## Core classes

### Execution and routing

| Class | Description |
|-------|-------------|
| `EmpathyLLMExecutor` | Default executor wrapping EmpathyLLM with routing |
| `AdaptiveModelRouter` | Route tasks to models based on historical telemetry performance |
| `ResilientExecutor` | Wrapper that adds resilience to LLM execution |

### Performance tracking

| Class | Fields | Description |
|-------|--------|-------------|
| `ModelPerformance` | `model_id: str`<br>`tier: str`<br>`success_rate: float`<br>`avg_latency_ms: float`<br>`avg_cost: float`<br>`sample_size: int`<br>`recent_failures: int = 0` | Performance metrics for a model on a specific task |

| Property | Type | Description |
|----------|------|-------------|
| `quality_score` | `float` | Calculate quality score for ranking models |

### Response and context

| Class | Fields | Description |
|-------|--------|-------------|
| `LLMResponse` | `content: str`<br>`model_id: str`<br>`provider: str`<br>`tier: str`<br>`tokens_input: int = 0`<br>`tokens_output: int = 0`<br>`cost_estimate: float = 0.0`<br>`latency_ms: int = 0`<br>`metadata: dict[str, Any] = field(default_factory=dict)` | Standardized response from an LLM execution |
| `ExecutionContext` | `user_id: str | None = None`<br>`workflow_name: str | None = None`<br>`step_name: str | None = None`<br>`task_type: str | None = None`<br>`provider_hint: str | None = None`<br>`tier_hint: str | None = None`<br>`timeout_seconds: int | None = None`<br>`session_id: str | None = None`<br>`metadata: dict[str, Any] = field(default_factory=dict)` | Context for an LLM execution |

| Property | Type | Description |
|----------|------|-------------|
| `input_tokens` | `int` | Alias for tokens_input (backwards compatibility) |
| `output_tokens` | `int` | Alias for tokens_output (backwards compatibility) |
| `model_used` | `str` | Alias for model_id (backwards compatibility) |
| `cost` | `float` | Alias for cost_estimate (backwards compatibility) |
| `total_tokens` | `int` | Total tokens used (input + output) |
| `success` | `bool` | Check if the response was successful (has content) |

## Authentication

### Strategy configuration

| Class | Fields | Description |
|-------|--------|-------------|
| `AuthStrategy` | `subscription_tier: SubscriptionTier = SubscriptionTier.PRO`<br>`default_mode: AuthMode = AuthMode.AUTO`<br>`small_module_threshold: int = 500`<br>`medium_module_threshold: int = 2000`<br>`loc_to_tokens_multiplier: float = 4.0`<br>`setup_completed: bool = True`<br>`prefer_subscription: bool = True`<br>`cost_optimization: bool = True`<br>`metadata: dict[str, Any] = field(default_factory=dict)` | Authentication strategy configuration |

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_recommended_mode` | `module_lines: int` | `AuthMode` | Get recommended authentication mode |
| `estimate_tokens` | `module_lines: int` | `int` | Estimate token count for module |
| `estimate_cost` | `module_lines: int, mode: AuthMode | None = None` | `dict[str, Any]` | Estimate cost for authentication mode |
| `get_pros_cons` | `module_lines: int` | `dict[str, Any]` | Get pros and cons for each mode |
| `to_dict` | | `dict[str, Any]` | Convert to dictionary |
| `from_dict` | `data: dict[str, Any]` | `AuthStrategy` | Create from dictionary |
| `save` | `path: Path | None = None` | `None` | Save strategy to file |
| `load` | `path: Path | None = None` | `AuthStrategy` | Load strategy from file |

### Enums and types

| Class | Description |
|-------|-------------|
| `SubscriptionTier` | Claude subscription tiers |
| `AuthMode` | Authentication mode selection |

## Resilience and fallbacks

### Circuit breaker

| Class | Fields | Description |
|-------|--------|-------------|
| `CircuitBreakerState` | `failure_count: int = 0`<br>`last_failure: datetime | None = None`<br>`is_open: bool = False`<br>`opened_at: datetime | None = None` | State of a circuit breaker for a provider |

| Class | Description |
|-------|-------------|
| `CircuitBreaker` | Circuit breaker to temporarily disable failing providers |

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_available` | `provider: str, tier: str | None = None` | `bool` | Check if provider is available |
| `record_success` | `provider: str, tier: str | None = None` | `None` | Record successful call |
| `record_failure` | `provider: str, tier: str | None = None` | `None` | Record failed call |
| `get_status` | | `dict[str, dict[str, Any]]` | Get circuit breaker status |
| `reset` | `provider: str | None = None, tier: str | None = None` | `None` | Reset circuit breaker |

## CLI commands

### Authentication commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_auth_setup` | `args: Any` | `int` | Run interactive authentication strategy setup |
| `cmd_auth_status` | `args: Any` | `int` | Show current authentication strategy configuration |
| `cmd_auth_reset` | `args: Any` | `int` | Reset/clear authentication strategy configuration |
| `cmd_auth_recommend` | `args: Any` | `int` | Get authentication recommendation for a specific file |
| `main` | | `int` | Main CLI entry point |

### Utility functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `configure_auth_interactive` | `module_lines: int = 1000` | `AuthStrategy` | Interactive authentication configuration (first-time setup) |
| `get_auth_strategy` | | `AuthStrategy` | Get the global authentication strategy |
| `count_lines_of_code` | `file_path: str | Path` | `int` | Count lines of code in a Python file |
| `get_module_size_category` | `module_lines: int` | `str` | Categorize module size |
| `print_registry` | `provider: str | None = None, format: str = 'table'` | `None` | Print the model registry |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `REALTIME_REQUIRED_TASKS` | `{'chat', 'interactive_debug', 'live_coding', 'user_query', 'workflow_step', 'critical_fix', 'security_incident', 'emergency_response', 'stream_analysis', 'realtime_monitoring'}` | Tasks requiring real-time response |
