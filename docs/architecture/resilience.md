---
type: architecture
name: resilience
tags: [resilience, fault-tolerance, circuit-breaker, retry, timeout, fallback, health-check]
source: resilience
---

# Resilience architecture

Fault-tolerance primitives — circuit breakers, retries, timeouts, fallbacks, and health checks.

## Purpose

The `resilience` module provides decorators and runtime classes that protect call sites from cascading failures: it handles transient errors through retry with exponential backoff, stops calling a dependency that is already failing through circuit breaking, bounds execution time via timeouts, and degrades gracefully through ordered fallback chains. It also exposes a health-check registry so external monitors can observe the state of registered components.

The module is **not** responsible for service discovery, connection pooling, load balancing, or any network transport. It wraps callables that already exist; it does not produce them.

## Key classes

| Class | Responsibility | File |
|---|---|---|
| `CircuitBreaker` | Tracks per-dependency failure counts and open/half-open/closed state transitions; raises `CircuitOpenError` when calls should be blocked | `resilience/circuit_breaker.py` |
| `CircuitState` | Enum of the three states a `CircuitBreaker` can occupy | `resilience/circuit_breaker.py` |
| `CircuitOpenError` | Raised on blocked calls; carries `name` and `reset_time` so callers can log or surface a useful message | `resilience/circuit_breaker.py` |
| `RetryConfig` | Holds backoff parameters (`backoff_factor`, `initial_delay`, `max_delay`, `jitter`) and computes per-attempt delay via `get_delay(attempt)` | `resilience/retry.py` |
| `Fallback` | Ordered list of callables tried in sequence; `execute()` walks `functions` and returns the first success, then `default_value` | `resilience/fallback.py` |
| `HealthCheck` | Registry of named check functions; `run_all()` / `run_all_sync()` execute every registered check and aggregate results into a `SystemHealth` | `resilience/health.py` |
| `HealthCheckResult` | Captures the outcome of one check: `status`, `latency_ms`, `message`, and freeform `details` | `resilience/health.py` |
| `SystemHealth` | Aggregated snapshot of all checks; `to_dict()` serialises it for HTTP health endpoints | `resilience/health.py` |
| `HealthStatus` | Enum of health severity levels used by both `HealthCheckResult` and `SystemHealth` | `resilience/health.py` |
| `TimeoutError` | Raised by `timeout` / `with_timeout` when the deadline is exceeded; carries `operation` and `timeout` for structured error messages | `resilience/timeout.py` |

## Data flow

An inbound call passes through whichever guards are applied as decorators. The typical composition from outermost to innermost is:

```
Caller
  │
  ▼
[timeout decorator]  ──── deadline exceeded ──► TimeoutError
  │                                              (or fallback value)
  ▼
[circuit_breaker decorator]
  │  CircuitBreaker.is_open?
  ├── YES ──────────────────────────────────────► CircuitOpenError
  │                                              (or decorator fallback)
  │  NO (CLOSED or HALF_OPEN)
  ▼
[retry decorator]
  │  attempt loop (up to RetryConfig.max_attempts)
  │    RetryConfig.get_delay(attempt) ──► sleep
  ├── all attempts failed ────────────────────► re-raise last exception
  │
  ▼
[fallback decorator / Fallback.execute()]
  │  walk Fallback.functions in order
  ├── first success ────────────────────────────► return result
  ├── all fail + default_value set ─────────────► return default_value
  └── all fail, no default ────────────────────► RuntimeError
                                                 'All fallbacks failed for {…}'

Side channel (independent of call path):
  HealthCheck.register(name) ──► registers a check function
  HealthCheck.run_all() ───────► [HealthCheckResult, …] ──► SystemHealth
                                  (aggregated status + to_dict() for
                                   HTTP /health endpoints)
```

`CircuitBreaker.record_success()` and `record_failure()` are called by the `circuit_breaker` decorator after each attempt to drive state transitions. `get_circuit_breaker(name)` retrieves any named breaker from the global registry, which is how the health-check layer can report circuit state without a direct import dependency on the protected function.

## Design decisions

**Four independent modules, one public surface.** Retry, circuit breaking, timeout, and fallback are each implemented in their own module and composed at the decorator level rather than baked into a single `Resilience` class. This means you can apply `@retry` without `@circuit_breaker`, or combine them in any order. The trade-off is that interaction effects between decorators (for example, whether a retry attempt resets the circuit-breaker's half-open call budget) are the caller's responsibility to reason about.

**`RetryConfig` as a first-class dataclass.** Retry parameters are extracted into `RetryConfig` rather than kept as closed-over locals in the decorator. This was a deliberate choice to support `retry_with_backoff(func, *args, config=my_config)`, which lets non-decorator call sites (tests, scripts) reuse the same backoff logic without applying a decorator.

**Global registries for `CircuitBreaker` and `HealthCheck`.** `get_circuit_breaker(name)` and `get_health_check()` return shared instances. This lets observability code (dashboards, `/health` handlers) inspect live breaker state without holding a reference to the original decorated function. The cost is that tests must reset global state explicitly between runs.

**`excluded_exceptions` on `CircuitBreaker`.** Failures that match `excluded_exceptions` do not increment the failure counter. This reflects the design intent that some exceptions (e.g., `ValueError` from bad input) should not count against a dependency's health — only infrastructure-level errors should trip the breaker.

## Extension points

- **Add a new health check**: call `HealthCheck.register(name, timeout, critical)` as a decorator on any async or sync function. The registered function must return a value that `HealthCheckResult` can wrap. Use `get_health_check()` to obtain the singleton instance, or pass a `HealthCheck` instance to `register_default_checks(health)` to populate standard Attune checks.

- **Customise retry behaviour**: construct a `RetryConfig` with your own `backoff_factor`, `initial_delay`, `max_delay`, and `retryable_exceptions`, then pass it to `retry_with_backoff(func, *args, config=my_config)`. The `get_delay(attempt)` method on `RetryConfig` is the single calculation point — override it in a subclass to implement a non-exponential schedule.

- **Add a fallback chain programmatically**: instantiate `Fallback(name="…")`, call `.add(func)` for each candidate in priority order, then call `.execute(*args, **kwargs)`. This is equivalent to the `@fallback` decorator but lets you build the chain at runtime rather than at import time.

- **Inspect or reset a circuit breaker by name**: use `get_circuit_breaker(name)` to retrieve a live `CircuitBreaker`, then call `get_stats()` to read counters or `reset()` to force it back to CLOSED — useful in integration tests or admin endpoints.

For usage examples, see the `resilience` reference documentation.
