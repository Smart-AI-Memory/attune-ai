---
type: task
feature: models
depth: task
generated_at: 2026-05-04T02:34:52.181447+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Work with models

Use the models module when you need to configure LLM authentication, route tasks to optimal models based on performance data, or manage provider fallback strategies.

## Prerequisites

- Access to the project source code
- Python development environment with pytest installed
- Familiarity with the `src/attune/models/` directory structure

## Configure authentication strategy

1. **Run the interactive setup** to configure your authentication preferences:
   ```bash
   python -m attune.models auth setup
   ```

2. **Choose your subscription tier** (Pro, Team, or Enterprise) based on your Claude subscription.

3. **Set cost optimization preferences** to balance between subscription usage and API calls.

4. **Verify your configuration** by checking the current status:
   ```bash
   python -m attune.models auth status
   ```

## Route tasks to optimal models

1. **Initialize the adaptive router** with your telemetry backend:
   ```python
   from attune.models import AdaptiveModelRouter

   router = AdaptiveModelRouter(telemetry_backend)
   ```

2. **Get the best model** for your specific workflow and constraints:
   ```python
   model = router.get_best_model(
       workflow="code_generation",
       stage="implementation",
       max_cost=0.50,
       min_success_rate=0.85
   )
   ```

3. **Check tier upgrade recommendations** if current performance is suboptimal:
   ```python
   should_upgrade, reason = router.recommend_tier_upgrade(
       workflow="code_generation",
       stage="implementation"
   )
   ```

## Set up circuit breaker protection

1. **Initialize the circuit breaker** to handle provider failures:
   ```python
   from attune.models import CircuitBreaker

   breaker = CircuitBreaker(
       failure_threshold=5,
       recovery_timeout_seconds=60
   )
   ```

2. **Check provider availability** before making calls:
   ```python
   if breaker.is_available("anthropic", "claude-3-sonnet"):
       # Proceed with LLM call
       pass
   ```

3. **Record call results** to update the circuit state:
   ```python
   # On success
   breaker.record_success("anthropic", "claude-3-sonnet")

   # On failure
   breaker.record_failure("anthropic", "claude-3-sonnet")
   ```

## Run tests

Execute the model-specific test suite to verify your changes:
```bash
pytest -k "models" -v
```

## Verify success

Your configuration is working correctly when:

- `auth status` shows your preferred settings without errors
- Model routing returns appropriate models for your task constraints
- Circuit breakers properly isolate failing providers
- All tests pass without regression
