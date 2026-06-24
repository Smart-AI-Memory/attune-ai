---
name: resilience
source: content/features/resilience.md
tags:
- resilience
- fault-tolerance
- retry
- circuit-breaker
- reliability
type: tip
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

## Notes & tips

- **Decorators are the common path; classes are for control.** Reach
  for `@retry` / `@circuit_breaker` / `@timeout` first.
- **Name your breakers.** A stable `name` shares one breaker across call
  sites via `get_circuit_breaker`.
- **Narrow `retryable_exceptions`.** Don't retry bugs.
- **Mind the async primitives.** `with_fallback` / `with_timeout` return
  / take coroutines.
