---
type: tip
name: resilience-tip
feature: resilience
depth: tip
generated_at: 2026-06-24T01:31:58.105100+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
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
