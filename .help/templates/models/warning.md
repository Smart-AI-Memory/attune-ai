---
type: warning
feature: models
depth: warning
generated_at: 2026-04-14T15:14:34.268037+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models cautions

## What to watch for

The models module handles LLM routing, authentication strategies, and circuit breaker patterns. Several components involve stateful behaviors and fallback logic that can produce unexpected results.

## Risk areas

### Circuit breaker state persistence

The `CircuitBreaker` class tracks failure counts and recovery timeouts across provider calls. When a provider fails repeatedly, the circuit breaker opens and blocks requests for 60 seconds by default. This state persists in memory, so provider availability can vary unexpectedly during long-running processes.

**Mitigation:** Check circuit breaker status with `get_status()` before assuming a provider is available. Use `reset()` to clear failure state during testing or recovery scenarios.

### Authentication strategy auto-selection

`AuthStrategy.get_recommended_mode()` chooses between subscription and API modes based on module size thresholds (500 and 2000 lines by default). The cost calculations in `estimate_cost()` use a fixed multiplier of 4.0 tokens per line of code, which may not reflect actual usage patterns for your codebase.

**Mitigation:** Review the thresholds and multiplier values for your use case. Test cost estimates against actual usage before deploying to production workloads.

### Adaptive router cache invalidation

`AdaptiveModelRouter` selects models based on historical performance metrics, but these metrics may become stale if the underlying telemetry data isn't regularly updated. The router's `get_best_model()` method returns the last successful model when no recent data is available, which could route requests to an outdated or suboptimal model.

**Mitigation:** Ensure your telemetry backend is actively collecting performance data. Monitor routing decisions with `get_routing_stats()` to verify the router is using current information.

### Provider fallback timing

The resilient executor attempts multiple providers when the primary fails, but fallback delays can accumulate unexpectedly. If your primary provider has intermittent issues, requests may take significantly longer than the normal timeout period.

**Mitigation:** Set explicit timeout values in your `ExecutionContext` and monitor total request latency, not just individual provider response times.

## How to avoid problems

1. **Test with realistic data volumes.** Authentication cost calculations and routing decisions depend heavily on input size. Test with files and workloads that match your production scale.

2. **Monitor circuit breaker state.** In production environments, check circuit breaker status periodically to identify providers experiencing sustained failures before users are affected.

3. **Validate telemetry data freshness.** The adaptive router relies on recent performance metrics. Ensure your telemetry collection is working and data is being updated regularly.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
