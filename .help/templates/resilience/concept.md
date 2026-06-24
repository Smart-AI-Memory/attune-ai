---
type: concept
name: resilience-concept
feature: resilience
depth: concept
generated_at: 2026-06-24T01:31:58.105100+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

## Overview

`attune.resilience` is a small toolkit of **fault-tolerance primitives**
for code that calls flaky things (LLM APIs, networks, subprocesses).
Five patterns, each in its own module and exported from
`attune.resilience`:

- **retry** — re-run on failure with exponential backoff + jitter.
- **circuit breaker** — stop calling a failing dependency until it
  recovers.
- **timeout** — bound how long a call may run.
- **fallback** — try alternates when the primary fails.
- **health checks** — aggregate component health into one status.

Each pattern has a **decorator** (the common case) and the underlying
**class/function** for programmatic use.

## Concepts

### retry

`@retry(...)` re-invokes a function on exception with exponential
backoff. Knobs: `max_attempts` (3), `backoff_factor` (2.0),
`initial_delay` (1.0), `max_delay` (60.0), `jitter` (True),
`retryable_exceptions` (which exceptions to retry — default all), and an
`on_retry` callback. `RetryConfig` holds the same settings as an object
(`get_delay(attempt)` computes the wait); `retry_with_backoff(func, *a,
config=...)` runs a call imperatively.

### circuit breaker

`@circuit_breaker(name=..., failure_threshold=5, reset_timeout=60.0,
half_open_max_calls=3)` trips OPEN after `failure_threshold`
consecutive failures, short-circuiting calls (raising `CircuitOpenError`)
until `reset_timeout` elapses, then probes in HALF_OPEN. `CircuitState`
is `CLOSED` / `OPEN` / `HALF_OPEN`. The underlying `CircuitBreaker`
class exposes `record_success` / `record_failure` / `reset` /
`get_stats` / `get_time_until_reset`; `get_circuit_breaker(name)` looks
one up from the shared registry by name.

### timeout

`@timeout(seconds, error_message=None, fallback=None)` bounds a call,
raising `ResilienceTimeoutError` (or returning `fallback`) on overrun.
For awaiting a coroutine with a bound, use `with_timeout(coro, seconds,
fallback_value=None)`.

### fallback

`@fallback(*fallback_funcs, default=None)` runs the alternates in order
when the decorated function raises. `with_fallback(primary, fallbacks,
default=None)` builds the same chain programmatically — **note it
returns an async wrapper** (await it), whereas the `@fallback` decorator
runs synchronously on a sync target (it returns a coroutine wrapper for
an `async def`). `Fallback(name, functions, default_value)` is the
underlying class (`add` / `execute`).

### health checks

`HealthCheck` aggregates named checks. Register each as a **decorator**
— `@hc.register(name, timeout=10.0, critical=False)` over a check
function — then `run_all()` (async) or `run_all_sync()` returns a
`SystemHealth` (`status`, `checks`, `to_dict()`). `HealthStatus` is
`HEALTHY` / `DEGRADED` / `UNHEALTHY` / `UNKNOWN`.
