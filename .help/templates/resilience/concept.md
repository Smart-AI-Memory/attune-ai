---
type: concept
feature: resilience
depth: concept
generated_at: 2026-05-04T02:41:54.401524+00:00
source_hash: ac7fa86c6fc160b49ba191ab5eb87d2a363ce5215faf5399776e3d9bd9112df7
status: generated
---

# Resilience

The resilience module provides fault-tolerance patterns that prevent failures in one part of your system from cascading to other parts.

## Core patterns

The module implements four resilience patterns that work together or independently:

**Circuit breakers** prevent repeated calls to failing services. A `CircuitBreaker` tracks failures and transitions between closed (normal), open (failing fast), and half-open (testing recovery) states. When the failure threshold is reached, the circuit opens and throws `CircuitOpenError` for new calls until the reset timeout expires.

**Retry logic** handles transient failures with exponential backoff. The `retry` decorator and `RetryConfig` class control how many attempts to make, how long to wait between them, and which exceptions trigger retries versus immediate failure.

**Fallback chains** provide graceful degradation when primary operations fail. A `Fallback` object tries functions in sequence until one succeeds, or returns a default value if all fail.

**Health monitoring** tracks system component status. The `HealthCheck` class runs diagnostic functions and aggregates results into a `SystemHealth` report showing which parts are healthy, degraded, or failing.

## Integration patterns

You can combine these patterns for layered protection:

```python
@circuit_breaker(name="api_client", failure_threshold=3)
@retry(max_attempts=2, backoff_factor=1.5)
@fallback(lambda: cached_response(), default=None)
@timeout(seconds=30.0)
def call_external_api():
    # Primary implementation
    pass
```

The circuit breaker prevents sustained load on a failing service, retries handle transient network issues, fallbacks provide alternative data sources, and timeouts prevent hanging operations.

## State management

Circuit breakers maintain shared state across function calls. Use `get_circuit_breaker()` to access a breaker by name, check its current state, or manually reset it after resolving the underlying issue.

Health checks register diagnostic functions that run on demand or on schedule. The global health check instance tracks all registered components and produces system-wide status reports.

## Exception handling

The module defines two specific exceptions: `CircuitOpenError` when a circuit breaker is open, and `TimeoutError` when operations exceed their time limit. Both inherit from standard Python exceptions and can be caught separately or together with other error handling patterns.
