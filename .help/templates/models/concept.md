---
feature: models
depth: concept
generated_at: 2026-04-13T17:00:06.834316+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models

## How it works

The unified model registry for Attune AI that handles LLM authentication, adaptive provider routing, and Claude subscription tier management.

The main building blocks are:

- **`ModelPerformance`** — Performance metrics for a model on a specific task.
- **`AdaptiveModelRouter`** — Routes tasks to models based on historical telemetry performance.
- **`SubscriptionTier`** — Claude subscription tiers.
- **`AuthMode`** — Authentication mode selection.
- **`AuthStrategy`** — Authentication strategy configuration.

Under the hood, this feature spans 22 source
files covering:

- CLI module execution for model commands
- Adaptive model routing based on historical telemetry
- Authentication strategy management through CLI commands

## What connects to it

This feature relates to: models, auth, llm.

Other parts of the codebase interact with
models through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ModelPerformance` | Performance metrics for a model on a specific task. | `src/attune/models/adaptive_routing.py` |
| `AdaptiveModelRouter` | Routes tasks to models based on historical telemetry performance. | `src/attune/models/adaptive_routing.py` |
| `SubscriptionTier` | Claude subscription tiers. | `src/attune/models/auth_strategy.py` |
| `AuthMode` | Authentication mode selection. | `src/attune/models/auth_strategy.py` |
| `AuthStrategy` | Authentication strategy configuration. | `src/attune/models/auth_strategy.py` |
