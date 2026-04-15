---
type: error
feature: models
depth: error
generated_at: 2026-04-14T15:14:18.283385+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models errors

Model authentication, provider routing, and circuit breaker failures in the Attune AI unified model registry.

## Common error signatures

- **Authentication failures**: `AuthStrategy.load()` raising `FileNotFoundError` when no auth configuration exists
- **Provider unavailability**: `CircuitBreaker.is_available()` returning `False` when failure threshold exceeded
- **Model routing errors**: `AdaptiveModelRouter.get_best_model()` raising `ValueError` when no models meet constraints
- **Token estimation failures**: `AuthStrategy.estimate_tokens()` producing negative values for malformed input
- **Circuit breaker state errors**: `CircuitBreakerState.is_open` becoming `True` after `failure_threshold` consecutive failures

## Where errors originate

Model errors typically start in these core components:

- **`EmpathyLLMExecutor.run()`** — LLM execution with adaptive routing that can fail when no suitable model is available or all providers are circuit-broken
- **`AdaptiveModelRouter.get_best_model()`** — Model selection based on telemetry constraints that fails when cost/latency requirements cannot be met
- **`CircuitBreaker.record_failure()`** — Provider failure tracking that opens circuits after repeated failures
- **`AuthStrategy.get_recommended_mode()`** — Authentication mode selection that can fail with invalid module size inputs
- **CLI commands in auth_cli.py** — Interactive setup and configuration commands that fail on filesystem permission errors or malformed config files

## How to diagnose

1. **Check circuit breaker status first.** Run `CircuitBreaker.get_status()` to see if providers are temporarily disabled. An open circuit breaker prevents model execution even when the underlying service is healthy.

2. **Verify authentication configuration.** Use `get_auth_strategy()` to load the current auth config. Missing or corrupted `AUTH_STRATEGY_FILE` causes downstream authentication failures.

3. **Examine model routing constraints.** When `get_best_model()` fails, check if your `max_cost`, `max_latency_ms`, or `min_success_rate` filters are too restrictive for available models in the registry.

4. **Review telemetry data quality.** Poor `ModelPerformance` metrics (low `sample_size`, high `recent_failures`) indicate insufficient data for reliable routing decisions.

5. **Test provider connectivity separately.** Circuit breaker failures often mask underlying network, authentication, or quota issues with the actual LLM providers.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
