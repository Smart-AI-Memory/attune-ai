---
name: resilience
source: content/features/resilience.md
tags:
- resilience
- fault-tolerance
- retry
- circuit-breaker
- reliability
type: troubleshooting
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

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
