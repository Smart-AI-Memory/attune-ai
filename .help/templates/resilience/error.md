---
type: error
name: resilience-error
feature: resilience
depth: error
generated_at: 2026-06-24T01:31:58.105100+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
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
