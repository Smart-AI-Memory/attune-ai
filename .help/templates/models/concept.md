---
feature: models
depth: concept
generated_at: 2026-06-03T02:40:23.607411+00:00
source_hash: eaf005e9abad245619a99d4824c4b03d726a7b59f62c01ae3437da4261b3bb55
status: generated
---

# Models

## How it works

LLM authentication, provider routing, and tier management.

The main building blocks are:

- **`ModelPerformance`** — Performance metrics for a model on a specific task.
- **`AdaptiveModelRouter`** — Route tasks to models based on historical telemetry performance.
- **`SubscriptionTier`** — Claude subscription tiers.
- **`AuthMode`** — Authentication mode selection.
- **`AuthStrategy`** — Authentication strategy configuration.

Under the hood, this feature spans 22 source
files covering:

- Enable running the models CLI as a module.
- Adaptive Model Routing based on historical telemetry.
- CLI commands for authentication strategy management.

## What connects to it

This feature relates to: models, auth, llm.

Other parts of the codebase interact with
models through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ModelPerformance` | Performance metrics for a model on a specific task. | `src/attune/models/adaptive_routing.py` |
| `AdaptiveModelRouter` | Route tasks to models based on historical telemetry performance. | `src/attune/models/adaptive_routing.py` |
| `SubscriptionTier` | Claude subscription tiers. | `src/attune/models/auth_strategy.py` |
| `AuthMode` | Authentication mode selection. | `src/attune/models/auth_strategy.py` |
| `AuthStrategy` | Authentication strategy configuration. | `src/attune/models/auth_strategy.py` |
