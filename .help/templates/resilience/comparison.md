---
type: comparison
name: resilience-comparison
feature: resilience
depth: comparison
generated_at: 2026-06-24T01:31:58.105100+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

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
