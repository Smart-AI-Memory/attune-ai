---
type: faq
name: models-faq
feature: models
depth: faq
generated_at: 2026-07-14T15:58:54.871943+00:00
source_hash: 52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668
status: generated
---

# Models FAQ

## How does Attune decide which model to use?

Each task type maps to a tier (`CHEAP`/`CAPABLE`/`PREMIUM`)
via `TASK_TIER_MAP`, and each tier maps to a model in
`MODEL_REGISTRY`. `get_tier_for_task` then `get_model` resolves it;
unknown tasks default to `CAPABLE`.

## Subscription or API — which should I use?

Use `AuthMode.AUTO` and let `get_recommended_mode` decide, or
run `attune auth setup` to pin a default. On `PRO`/`API_ONLY`
accounts `AUTO` always picks the API; only `MAX`/`ENTERPRISE`
accounts get size-based selection (subscription for small/medium
modules, API for large).

## How do I see the cost of a model?

`get_pricing_for_model(model_id)` returns per-million input and
output costs; `ModelInfo.cost_per_1k_input` / `cost_per_1k_output`
give the per-1k equivalents (they are properties).

## Why did my task pick a more expensive model than I expected?

Either the task classifies into a higher tier, or an
`AdaptiveModelRouter` escalated based on telemetry. Check
`get_tier_for_task(task)` and, if adaptive, `get_routing_stats`.

## What providers are supported?

Anthropic. `ModelProvider` has a single member today and
`get_model` raises `ValueError` for anything else.
