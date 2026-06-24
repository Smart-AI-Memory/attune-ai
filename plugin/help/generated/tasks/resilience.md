---
name: resilience
source: content/features/resilience.md
tags:
- resilience
- fault-tolerance
- retry
- circuit-breaker
- reliability
type: task
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

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
