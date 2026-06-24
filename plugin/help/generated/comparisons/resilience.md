---
name: resilience
source: content/features/resilience.md
tags:
- resilience
- fault-tolerance
- retry
- circuit-breaker
- reliability
type: comparison
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
