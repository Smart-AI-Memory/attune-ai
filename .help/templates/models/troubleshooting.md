---
type: troubleshooting
feature: models
depth: troubleshooting
generated_at: 2026-04-14T15:14:51.743899+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Troubleshoot models

## Before you start

The models feature handles LLM authentication, adaptive routing between providers, and performance-based model selection. Issues often stem from authentication misconfiguration, circuit breaker states, or telemetry data problems.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Authentication errors or API failures | Run `python -m attune.models auth status` to verify your authentication strategy |
| Models not routing to expected providers | Check `AdaptiveModelRouter.get_routing_stats()` for telemetry data and circuit breaker status |
| High costs or slow responses | Examine `ModelPerformance` metrics and verify tier assignments match your workflow requirements |
| Circuit breaker blocking requests | Use `CircuitBreaker.get_status()` to see which providers are marked as failing |
| Silent failures with empty responses | Verify `LLMResponse.success` property and check for missing model configurations |

## Step-by-step diagnosis

1. **Test authentication independently.**
   Run the auth CLI commands to isolate configuration issues:
   ```bash
   python -m attune.models auth status
   python -m attune.models auth recommend path/to/your/file.py
   ```

2. **Check circuit breaker states.**
   When models fail intermittently, examine circuit breaker status:
   ```python
   from attune.models import CircuitBreaker
   cb = CircuitBreaker()
   print(cb.get_status())
   ```

3. **Verify model registry and routing.**
   Inspect available models and their performance data:
   ```python
   from attune.models import print_registry, AdaptiveModelRouter
   print_registry()  # Show all available models

   # Check routing decisions for your workflow
   router = AdaptiveModelRouter(your_telemetry)
   stats = router.get_routing_stats("your_workflow", "your_stage")
   ```

4. **Enable debug logging.**
   Set logging to DEBUG to see routing decisions and API calls:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

5. **Test with minimal execution context.**
   Create a basic `ExecutionContext` to isolate the failure:
   ```python
   from attune.models import EmpathyLLMExecutor, ExecutionContext

   executor = EmpathyLLMExecutor()
   context = ExecutionContext(
       workflow_name="test",
       step_name="debug",
       task_type="your_task_type"
   )
   response = executor.run("your_task", "test prompt", context=context)
   ```

## Common fixes

- **Reset authentication configuration.**
  ```bash
  python -m attune.models auth reset
  python -m attune.models auth setup
  ```

- **Clear circuit breaker state.**
  ```python
  from attune.models import CircuitBreaker
  cb = CircuitBreaker()
  cb.reset()  # Clear all provider states
  cb.reset("anthropic")  # Clear specific provider
  ```

- **Update model performance data.**
  Stale or missing telemetry can cause poor routing decisions. Verify your `TelemetryStore` has recent data for your workflows.

- **Check authentication strategy thresholds.**
  If costs are unexpectedly high, verify your `AuthStrategy` configuration:
  ```python
  from attune.models import get_auth_strategy
  strategy = get_auth_strategy()
  print(f"Small module threshold: {strategy.small_module_threshold}")
  print(f"Prefer subscription: {strategy.prefer_subscription}")
  ```

- **Verify task-to-tier mapping.**
  Some tasks require specific model tiers. Check that your task type is mapped to an available tier in the registry.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
