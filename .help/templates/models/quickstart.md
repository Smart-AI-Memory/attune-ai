---
type: quickstart
feature: models
depth: quickstart
generated_at: 2026-04-14T15:15:23.302638+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Quickstart: models

Execute LLM tasks with intelligent model routing and authentication.

```python
from attune.models import EmpathyLLMExecutor

# Run your first LLM task
executor = EmpathyLLMExecutor()
response = executor.run(
    task_type="code_review",
    prompt="Review this Python function for potential issues",
    system="You are a senior Python developer"
)
print(f"Model used: {response.model_id}")
print(f"Response: {response.content}")
```

Expected output:
```
Model used: claude-3-5-sonnet-20241022
Response: I'd be happy to review the Python function...
```

## Set up authentication

Configure your API credentials for optimal routing:

```bash
python -m attune.models auth setup
```

This launches an interactive setup that configures authentication based on your subscription tier and usage patterns.

## Route tasks by performance

Use adaptive routing to automatically select the best model for each task:

```python
from attune.models import AdaptiveModelRouter
from attune.telemetry import get_telemetry_store

router = AdaptiveModelRouter(get_telemetry_store())
best_model = router.get_best_model(
    workflow="code_analysis",
    stage="review",
    max_cost=0.05  # Maximum cost per request
)
print(f"Recommended model: {best_model}")
```

**Next:** Configure provider settings with `python -m attune.models auth status` to see your current authentication strategy and optimize for your workflow.
