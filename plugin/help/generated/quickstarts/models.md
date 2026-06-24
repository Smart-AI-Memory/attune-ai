---
name: models
source: content/features/models.md
tags:
- models
- auth
- llm
type: quickstart
---

# LLM authentication, provider routing, and tier management

## Quickstart

Inspect the active routing and pricing in a single Python call:

```python
from attune.models import get_tier_for_task, get_model, get_pricing_for_model

tier = get_tier_for_task("generate_code")     # ModelTier.CAPABLE
model = get_model("anthropic", tier.value)    # ModelInfo | None
print(model.id, model.cost_per_1k_input)      # cost_per_1k_input is a property

pricing = get_pricing_for_model(model.id)     # {"input": ..., "output": ...} per million
print(pricing)
```

`cost_per_1k_input` and `cost_per_1k_output` are **properties** — read
them, don't call them. `get_model` returns `None` if no model is
registered for that provider/tier, so guard the result before using it.

From the shell, the same information and your auth posture:

```bash
attune auth status          # current auth strategy
attune provider show        # current provider
```
