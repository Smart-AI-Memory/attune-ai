# Resilience

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

<!-- attune-generated: source_hash=5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6 feature=resilience kind=how-to generated_at=2026-06-24 -->
