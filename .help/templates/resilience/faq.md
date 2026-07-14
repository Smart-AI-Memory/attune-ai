---
type: faq
name: resilience-faq
feature: resilience
depth: faq
generated_at: 2026-07-14T15:59:00.322278+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
---

# Resilience FAQ

## Which resilience pattern should I use?

retry for transient blips, circuit breaker when a dependency is
down, timeout for hangs, fallback for an acceptable alternate, health
checks to report status.

## Is the fallback API sync or async?

The `@fallback` decorator is synchronous; `with_fallback(...)`
returns an async wrapper you must await. `with_timeout` is also async.

## How do I reset a tripped circuit breaker?

`get_circuit_breaker(name).reset()`, or wait `reset_timeout`
for it to probe in HALF_OPEN.

## How do I stop retrying on non-transient errors?

Pass `retryable_exceptions=(SomeError, ...)` to `@retry` so only
those retry.
