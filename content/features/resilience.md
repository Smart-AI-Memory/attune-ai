---
feature: resilience
summary: Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks
tags: [resilience, fault-tolerance, retry, circuit-breaker, reliability]
source_globs:
  - src/attune/resilience/**
nav:
  help: resilience
  mkdocs:
    how-to: how-to/resilience
    architecture: architecture/resilience
    reference: reference/resilience
---

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

## Quickstart

Add retry to a flaky call with one decorator:

```python
from attune.resilience import retry


@retry(max_attempts=3, initial_delay=0.1)
def load_value() -> int:
    return 42


print(load_value())
```

## Tasks

### Retry a flaky call with backoff

```python
from attune.resilience import retry


@retry(max_attempts=5, backoff_factor=2.0, initial_delay=0.1)
def fetch() -> str:
    return "ok"


print(fetch())
```

**Verify:** the function runs normally on success; on exception it
retries up to `max_attempts`, sleeping `initial_delay *
backoff_factor**n` (capped at `max_delay`, with jitter).

### Guard a dependency with a circuit breaker

```python
from attune.resilience import circuit_breaker, get_circuit_breaker


@circuit_breaker(name="api", failure_threshold=5, reset_timeout=30.0)
def call_api() -> str:
    return "ok"


print(call_api())
print(get_circuit_breaker("api").get_stats())
```

**Verify:** `get_circuit_breaker("api")` returns the registered
`CircuitBreaker`; `get_stats()` reports `name`, `state`,
`failure_count`, `success_count`, `time_until_reset`. After
`failure_threshold` consecutive failures the breaker opens and calls
raise `CircuitOpenError` until `reset_timeout` passes.

### Bound a call with a timeout

```python
from attune.resilience import timeout


@timeout(seconds=5.0)
def quick() -> str:
    return "done"


print(quick())
```

**Verify:** returns normally within the bound; raises
`ResilienceTimeoutError` (or returns the `fallback`) on overrun.

### Fall back to alternates

```python
import asyncio

from attune.resilience import fallback, with_fallback


@fallback(lambda: "from-fallback")          # decorator: synchronous
def risky() -> str:
    raise RuntimeError("primary failed")


print(risky())


def primary() -> str:
    raise ValueError("boom")


safe = with_fallback(primary, [lambda: "backup"])   # returns async wrapper
print(asyncio.run(safe()))
```

**Verify:** the `@fallback` decorator returns the first alternate's
result synchronously; `with_fallback(...)` returns an **async** callable
— `await` it (here via `asyncio.run`).

### Aggregate component health

```python
from attune.resilience import HealthCheck

hc = HealthCheck()


@hc.register("db")               # register is a decorator
def check_db() -> bool:
    return True


health = hc.run_all_sync()
print(health.status, health.to_dict())
```

**Verify:** `register(name, ...)` is a **decorator** — apply it over a
check function (returning a bool/dict), not as `register(name, fn)`.
`run_all_sync()` returns a `SystemHealth` whose `status` is a
`HealthStatus` and `to_dict()` serializes the result; `run_all()` is the
async variant.

## Reference

| Symbol | Kind | Purpose |
|--------|------|---------|
| `retry(max_attempts=3, backoff_factor=2.0, initial_delay=1.0, max_delay=60.0, jitter=True, retryable_exceptions=None, on_retry=None)` | decorator | Retry with backoff. |
| `RetryConfig(...)` / `retry_with_backoff(func, *a, config=None)` | class / fn | Retry config + imperative runner. |
| `circuit_breaker(name=None, failure_threshold=5, reset_timeout=60.0, half_open_max_calls=3, ...)` | decorator | Circuit breaker. |
| `CircuitBreaker(name, ...)` / `get_circuit_breaker(name)` | class / fn | Breaker object + registry lookup. |
| `CircuitState` | enum | `CLOSED` / `OPEN` / `HALF_OPEN`. |
| `CircuitOpenError` | exception | Raised when the breaker is open. |
| `timeout(seconds, error_message=None, fallback=None)` | decorator | Bound a call. |
| `with_timeout(coro, seconds, fallback_value=None)` | async fn | Bound a coroutine. |
| `ResilienceTimeoutError` | exception | Raised on overrun. |
| `fallback(*fns, default=None, log_failures=True)` | decorator (sync) | Try alternates. |
| `with_fallback(primary, fallbacks, default=None)` | fn → **async** wrapper | Programmatic fallback chain. |
| `Fallback(name, functions, default_value=None)` | class | `add` / `execute`. |
| `HealthCheck(version="unknown")` | class | `register(name, timeout=10.0, critical=False)` **decorator**, `run_all` (async), `run_all_sync`. |
| `HealthStatus` / `SystemHealth` | enum / class | `HEALTHY`/`DEGRADED`/`UNHEALTHY`/`UNKNOWN`; aggregate result. |

## Comparison

| Pattern | Use when | Failure behavior |
|---------|----------|------------------|
| retry | transient failures that often succeed on a re-try | re-runs, then re-raises |
| circuit breaker | a dependency is down and retrying just piles on | short-circuits with `CircuitOpenError` |
| timeout | a call may hang | raises `ResilienceTimeoutError` |
| fallback | an alternate result is acceptable | returns the alternate / default |
| health check | you need one status across components | reports `HealthStatus` |

retry and circuit breaker compose: retry handles the occasional blip;
the breaker stops the bleeding when a dependency is genuinely down.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `with_fallback(...)()` returns a coroutine / `RuntimeWarning: never awaited` | `with_fallback` returns an **async** wrapper | `await` it (or `asyncio.run`); or use the sync `@fallback` decorator | high |
| Calls keep raising `CircuitOpenError` | breaker is OPEN after `failure_threshold` failures | wait `reset_timeout`, or `get_circuit_breaker(name).reset()` | medium |
| Retries never stop / take too long | `max_attempts` / `max_delay` too high | tune the knobs; set `retryable_exceptions` to narrow what retries | medium |
| Every exception retries, even bugs | `retryable_exceptions` left as default (all) | pass the specific exception tuple | medium |

### Risk areas

- **`with_fallback` / `with_timeout` are async.** The `@fallback`
  decorator is synchronous on a sync target; `with_fallback` returns an
  async wrapper regardless.
- **Breaker state is shared by `name`.** Two decorators with the same
  `name` share one breaker via the registry.
- **Unbounded `retryable_exceptions`.** Defaulting to all exceptions
  retries programming errors too.

### Diagnosis order

1. Coroutine-not-awaited? You used an async primitive (`with_fallback`/
   `with_timeout`) synchronously.
2. `CircuitOpenError`? Inspect `get_circuit_breaker(name).get_stats()`.
3. Slow retries? Check `max_attempts` / `max_delay` / `backoff_factor`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** Which resilience pattern should I use?
  **A:** retry for transient blips, circuit breaker when a dependency is
  down, timeout for hangs, fallback for an acceptable alternate, health
  checks to report status.
- **Q:** Is the fallback API sync or async?
  **A:** The `@fallback` decorator is synchronous; `with_fallback(...)`
  returns an async wrapper you must await. `with_timeout` is also async.
- **Q:** How do I reset a tripped circuit breaker?
  **A:** `get_circuit_breaker(name).reset()`, or wait `reset_timeout`
  for it to probe in HALF_OPEN.
- **Q:** How do I stop retrying on non-transient errors?
  **A:** Pass `retryable_exceptions=(SomeError, ...)` to `@retry` so only
  those retry.

## Notes & tips

- **Decorators are the common path; classes are for control.** Reach
  for `@retry` / `@circuit_breaker` / `@timeout` first.
- **Name your breakers.** A stable `name` shares one breaker across call
  sites via `get_circuit_breaker`.
- **Narrow `retryable_exceptions`.** Don't retry bugs.
- **Mind the async primitives.** `with_fallback` / `with_timeout` return
  / take coroutines.

## Design & extension

### Design decisions

- **Decorator + class for each pattern.** The decorator covers the
  common case; the class/function gives programmatic control.
- **Registry-backed breakers.** `circuit_breaker(name=...)` shares state
  by name so multiple call sites to one dependency trip together.
- **Backoff with jitter by default.** `retry` spreads retries to avoid
  thundering-herd.

### Extension points

- **Custom retry policy:** build a `RetryConfig` and use
  `retry_with_backoff(func, config=...)`.
- **Inspect/reset breakers:** `get_circuit_breaker(name)` →
  `get_stats()` / `reset()`.
- **Custom health checks:** `@hc.register(name)` over a check function,
  then `run_all_sync()`.
