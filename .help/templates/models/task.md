---
type: task
feature: models
depth: task
generated_at: 2026-04-14T15:13:19.096243+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Work with models

Use the models module when you need to configure authentication strategies, route tasks to optimal models based on performance telemetry, or manage provider fallback policies.

## Prerequisites

- Access to the project source code
- Python environment with Attune AI dependencies installed
- Valid API credentials for your chosen provider (Anthropic, OpenAI, etc.)

## Configure authentication strategy

1. **Run the interactive setup** to configure your authentication preferences:
   ```bash
   python -m attune.models auth setup
   ```

2. **Specify your module size thresholds** when prompted. The system uses these to recommend subscription vs API usage based on token estimates.

3. **Set your subscription tier** (Free, Pro, Team) to optimize cost calculations.

4. **Verify your configuration** works correctly:
   ```bash
   python -m attune.models auth status
   ```

You should see your subscription tier, default mode, and threshold settings displayed.

## Route tasks with adaptive model selection

1. **Initialize the router** with your telemetry backend:
   ```python
   from attune.models import AdaptiveModelRouter

   router = AdaptiveModelRouter(telemetry=your_telemetry_store)
   ```

2. **Get the optimal model** for your specific task:
   ```python
   model_id = router.get_best_model(
       workflow="code_review",
       stage="analysis",
       max_cost=0.10,
       max_latency_ms=5000,
       min_success_rate=0.85
   )
   ```

3. **Check if a tier upgrade is recommended** based on recent performance:
   ```python
   should_upgrade, reason = router.recommend_tier_upgrade(
       workflow="code_review",
       stage="analysis"
   )
   ```

The router returns `True` and a reason string if upgrading would improve performance metrics.

## Handle provider failures with circuit breakers

1. **Initialize circuit breaker protection** for your providers:
   ```python
   from attune.models import CircuitBreaker

   breaker = CircuitBreaker(
       failure_threshold=3,
       recovery_timeout_seconds=120
   )
   ```

2. **Check provider availability** before making requests:
   ```python
   if breaker.is_available("anthropic", "pro"):
       # Safe to make request
       response = make_llm_request()
       breaker.record_success("anthropic", "pro")
   else:
       # Use fallback provider
   ```

3. **Record failures** when requests fail:
   ```python
   try:
       response = make_llm_request()
   except Exception:
       breaker.record_failure("anthropic", "pro")
       raise
   ```

The circuit breaker automatically opens after the failure threshold is reached, preventing further requests until the recovery timeout expires.

## Verify success

- **Authentication setup**: Run `python -m attune.models auth status` and confirm your settings are correct
- **Model routing**: Check that `get_best_model()` returns valid model IDs for your workflows
- **Circuit breaker**: Verify that `get_status()` shows expected provider states after recording successes/failures

## Key files

- `src/attune/models/auth_strategy.py` — Authentication configuration and cost estimation
- `src/attune/models/routing.py` — Adaptive model routing based on telemetry
- `src/attune/models/circuit_breaker.py` — Provider failure handling
- `src/attune/models/executor.py` — LLM execution with routing and resilience
