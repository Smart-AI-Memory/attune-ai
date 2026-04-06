---
feature: models
depth: concept
generated_at: 2026-04-06T04:33:39.838730+00:00
source_hash: 5281a9cce870400fa1f93a29dd9b940cdc17f1029494b1b3ceec79cbe9969f3c
status: generated
---

# Models

## How it works

Unified model registry with adaptive routing, authentication strategy management, and circuit breaker protection for LLM providers.

The main building blocks are:

- **`ModelPerformance`** — Performance metrics for a model on a specific task.
- **`AdaptiveModelRouter`** — Route tasks to models based on historical telemetry performance.
- **`SubscriptionTier`** — Claude subscription tiers.
- **`AuthMode`** — Authentication mode selection.
- **`AuthStrategy`** — Authentication strategy configuration.

Under the hood, this feature spans 46 source
files covering:

- Unified Model Registry for Attune AI
- Adaptive Model Routing based on historical telemetry
- CLI commands for authentication strategy management
- Authentication Strategy for Claude Subscriptions vs API

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
