---
type: quickstart
name: models-quickstart
feature: models
depth: quickstart
generated_at: 2026-05-16T06:19:45.852411+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Quickstart: Model Routing and Authentication

Route your first LLM call through Attune's model registry and confirm the authentication strategy is configured correctly.

```python
from attune.models import get_auth_strategy, EmpathyLLMExecutor

strategy = get_auth_strategy()
print(strategy.to_dict())
```

Expected output (values reflect your local config):

```
{
  "subscription_tier": "pro",
  "default_mode": "auto",
  "prefer_subscription": true,
  "cost_optimization": true,
  "setup_completed": true,
  ...
}
```

If `setup_completed` is `false`, complete step 1 before continuing.

## Prerequisites

- The project is cloned and installed locally
- An Anthropic API key or Claude subscription

## Step 1: Set up your authentication strategy

Run the interactive setup to configure your subscription tier and cost preferences:

```python
from attune.models import configure_auth_interactive

strategy = configure_auth_interactive(module_lines=1000)
strategy.save()
```

The CLI equivalent is:

```
python -m attune.models auth setup
```

## Step 2: Run a task through the executor

Create an `EmpathyLLMExecutor` and run a task. The executor automatically selects the best model for the task type:

```python
from attune.models import EmpathyLLMExecutor

executor = EmpathyLLMExecutor(provider="anthropic")
response = executor.run(
    task_type="user_query",
    prompt="Summarize the purpose of adaptive model routing.",
)

print(response.model_id)       # which model was selected
print(response.cost_estimate)  # estimated cost in USD
print(response.content)        # the response text
```

## Step 3: Inspect routing statistics

Check how the `AdaptiveModelRouter` scored models for your workflow:

```python
from attune.models import AdaptiveModelRouter, get_telemetry_store

router = AdaptiveModelRouter(telemetry=get_telemetry_store())
stats = router.get_routing_stats(workflow="my_workflow", days=7)
print(stats)
```

## What you just did

- Loaded your `AuthStrategy` and confirmed it is configured
- Ran a prompt through `EmpathyLLMExecutor`, which selected a model from the registry based on task type
- Queried `AdaptiveModelRouter` for routing statistics drawn from historical telemetry

## Next:

Say **"how does adaptive model routing work?"** to understand how `ModelPerformance.quality_score`, success rates, and latency constraints combine to pick the best model for each task.
