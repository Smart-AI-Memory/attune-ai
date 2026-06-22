---
type: reference
feature: resilience
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: fc9bb0156f639a552b0e370a4a654fbc4e2ed99680ac269383522a95975a9464
status: generated
---

# Resilience reference

Protect your functions from failures, timeouts, and cascading errors with circuit breakers, retry logic, fallbacks, and health monitoring.

## Classes

### CircuitBreaker

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | | Circuit breaker identifier |
| `failure_threshold` | int | 5 | Failures before opening circuit |
| `reset_timeout` | float | 60.0 | Seconds before allowing half-open attempts |
| `half_open_max_calls` | int | 3 | Max calls in half-open state |
| `excluded_exceptions` | tuple[type[Exception], ...] | () | Exceptions that don't count as failures |

| Property | Type | Description |
|----------|------|-------------|
| `state` | CircuitState | Current circuit state, checking for timeout |
| `is_open` | bool | Whether circuit is open (failing fast) |
| `is_closed` | bool | Whether circuit is closed (normal operation) |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `record_success` |  | None | Mark a successful operation |
| `record_failure` | exception: Exception | None | Mark a failed operation |
| `get_time_until_reset` |  | float | Seconds until circuit can transition to half-open |
| `reset` |  | None | Manually reset circuit to closed state |
| `get_stats` |  | dict[str, Any] | Get circuit breaker statistics |

### Fallback

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | | Fallback chain identifier |
| `functions` | list[Callable] | [] | List of fallback functions |
| `default_value` | Any \| None | None | Value returned if all fallbacks fail |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add` | func: Callable | Fallback | Add a function to the fallback chain |
| `execute` | *args: Any, **kwargs: Any | Any | Execute the fallback chain |

### HealthCheckResult

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | | Name of the health check |
| `status` | HealthStatus | | Health status result |
| `message` | str | '' | Descriptive message |
| `latency_ms` | float | 0.0 | Check execution time in milliseconds |
| `details` | dict[str, Any] | {} | Additional diagnostic information |
| `timestamp` | datetime | now() | When the check was performed |

### SystemHealth

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | HealthStatus | | Overall system health status |
| `checks` | list[HealthCheckResult] | | Individual health check results |
| `version` | str | 'unknown' | System version |
| `uptime_seconds` | float | 0.0 | System uptime |
| `timestamp` | datetime | now() | When the health summary was generated |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` |  | dict[str, Any] | Convert to dictionary format |

### RetryConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_attempts` | int | 3 | Maximum number of retry attempts |
| `backoff_factor` | float | 2.0 | Exponential backoff multiplier |
| `initial_delay` | float | 1.0 | Initial delay in seconds |
| `max_delay` | float | 60.0 | Maximum delay between retries |
| `jitter` | bool | True | Whether to add random jitter |
| `retryable_exceptions` | tuple[type[Exception], ...] | (Exception,) | Exception types that trigger retries |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_delay` | attempt: int | float | Calculate delay for given attempt number |

### Exception Classes

| Class | Parameters | Description |
|-------|------------|-------------|
| `CircuitOpenError` | name: str, reset_time: float | Raised when circuit breaker is open |
| `TimeoutError` | operation: str, timeout: float | Raised when an operation times out |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `circuit_breaker` | name: str \| None = None, failure_threshold: int = 5, reset_timeout: float = 60.0, half_open_max_calls: int = 3, excluded_exceptions: tuple[type[Exception], ...] \| None = None, fallback: Callable[..., T] \| None = None | Callable | CircuitOpenError | Decorator to wrap a function with circuit breaker protection |
| `fallback` | *fallback_funcs: Callable, default: Any \| None = None, log_failures: bool = True | Callable | RuntimeError | Decorator to add fallback behavior to a function |
| `get_circuit_breaker` | name: str | CircuitBreaker \| None |  | Get a registered circuit breaker by name |
| `get_health_check` |  | HealthCheck |  | Get or create global health check instance |
| `register_default_checks` | health: HealthCheck | None |  | Register default health checks for Attune AI |
| `retry` | max_attempts: int = 3, backoff_factor: float = 2.0, initial_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True, retryable_exceptions: tuple[type[Exception], ...] \| None = None, on_retry: Callable[[Exception, int], None] \| None = None | Callable | last_exception, RuntimeError | Decorator for retrying functions with exponential backoff |
| `retry_with_backoff` | func: Callable[..., T], *args: Any, config: RetryConfig \| None = None, **kwargs: Any | T | last_exception, RuntimeError | Execute a function with retry logic |
| `timeout` | seconds: float, error_message: str \| None = None, fallback: Callable[..., T] \| None = None | Callable | TimeoutError | Decorator to add timeout to a function |
| `with_fallback` | primary: Callable[..., T], fallbacks: list[Callable[..., T]], default: T \| None = None | Callable[..., T] |  | Create a function that tries primary then fallbacks |
| `with_timeout` | coro: Any, seconds: float, fallback_value: T \| None = None | T | TimeoutError | Execute a coroutine with a timeout |

### Raises

| Exception | Message | Context |
|-----------|---------|---------|
| RuntimeError | 'All fallbacks failed for {...}' | All fallback functions failed |
| RuntimeError | 'Unexpected retry loop exit' | Internal retry mechanism error |
| TimeoutError | 'coroutine' | Coroutine execution timeout |

## Enums

### CircuitState

Circuit breaker states for tracking failure conditions.

### HealthStatus

Health status levels for system monitoring.

## Health Check Manager

The `HealthCheck` class monitors system components with configurable checks.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | version: str = 'unknown' |  | Initialize health check manager |
| `register` | name: str, timeout: float = 10.0, critical: bool = False | Callable | Register a new health check |
| `run_check` | name: str | HealthCheckResult | Run a single health check |
| `run_all` |  | SystemHealth | Run all health checks asynchronously |
| `run_all_sync` |  | SystemHealth | Run all health checks synchronously |
