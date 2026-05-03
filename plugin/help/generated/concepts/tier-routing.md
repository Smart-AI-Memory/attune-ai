---
name: tier-routing
source: src/attune/workflows/base.py
summary: This template explains how to implement model tier routing to automatically
  select Claude models (Haiku, Sonnet, or Opus) based on task complexity, reducing
  API costs by 80–96% while maintaining output quality through a tier map that assigns
  cost-efficient models to simple tasks and capable models to complex ones.
tags:
- architecture
- cost-optimization
type: concept
---

# Model Tier Routing

Model tier routing automatically selects the appropriate Claude model—Haiku, Sonnet, or Opus—based on the complexity of each task in your workflow. Simple tasks are handled by cost-efficient models, while complex tasks escalate to more capable ones.

## Why use tier routing?

Running every workflow stage on a premium model is rarely necessary and quickly becomes expensive. Tier routing reduces API costs by 80–96% by matching model capability to actual task requirements, without compromising output quality.

## How it works

Each workflow defines a `tier_map` that assigns a model tier to each stage:

| Tier | Intended use |
|------|-------------|
| `CHEAP` | High-volume, straightforward tasks (e.g., classification, formatting) |
| `CAPABLE` | Moderate reasoning and generation tasks |
| `PREMIUM` | Complex analysis, nuanced reasoning, or high-stakes outputs |

At runtime, the authentication strategy resolves each tier to a specific model ID. If a cheaper tier fails, the system automatically escalates to the next tier—ensuring reliability without requiring manual intervention.

## Example

```python
tier_map = {
    "initial_scan": ModelTier.CHEAP,
    "deep_review":  ModelTier.PREMIUM,
}
```

In this example, the `initial_scan` stage runs on Haiku to minimize cost, while `deep_review` escalates to Opus for thorough analysis.

## Related topics

No related topics yet.
