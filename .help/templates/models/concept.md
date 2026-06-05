---
type: concept
name: models-concept
feature: models
depth: concept
generated_at: 2026-06-04T23:45:26.739351+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models

The `models` subsystem is attune's unified layer for selecting which LLM runs a given task, how it authenticates, and what happens when a provider fails.

## Core responsibilities

Three concerns work together here:

1. **Model registry and tier mapping.** `MODEL_REGISTRY` catalogs available models grouped by tier (`CHEAP_TASKS`, `CAPABLE_TASKS`, `PREMIUM_TASKS`). When a workflow stage runs, the registry answers "which model is appropriate for this task type at this cost ceiling?"

2. **Adaptive routing.** `AdaptiveModelRouter` consults historical telemetry — not static configuration — to pick the best model for a given workflow and stage. It tracks per-model outcomes in `ModelPerformance`, which records `success_rate`, `avg_latency_ms`, `avg_cost`, and `recent_failures` for each task. The derived `quality_score` property combines these signals into a single ranking value. You can also call `recommend_tier_upgrade` to find out whether moving to a higher tier would improve outcomes on a specific workflow stage.

3. **Authentication strategy.** `AuthStrategy` decides whether a request should use a Claude subscription or the API directly (`AuthMode`), based on `SubscriptionTier` and module size thresholds. For a file with 800 lines of code, `get_recommended_mode` checks it against `small_module_threshold` (default 500) and `medium_module_threshold` (default 2000) to return the appropriate `AuthMode`. Cost estimates, pros/cons comparisons, and token projections are available through `estimate_cost`, `get_pros_cons`, and `estimate_tokens`.

## How the pieces fit together

A request flows through the subsystem in this order:

```
task type + workflow stage
        │
        ▼
AdaptiveModelRouter.get_best_model()   ← reads ModelPerformance from telemetry
        │
        ▼
EmpathyLLMExecutor.run()               ← wraps the selected model with routing
        │
        ▼
LLMResponse                            ← standardized result with model_id,
                                          tier, cost_estimate, latency_ms
```

`ExecutionContext` carries per-call metadata — `workflow_name`, `step_name`, `provider_hint`, `tier_hint` — that `EmpathyLLMExecutor` can use to override the default routing decision.

## Resilience

`CircuitBreaker` sits between the executor and each provider. It tracks `failure_count` and `last_failure` in a `CircuitBreakerState` record and opens the circuit after a configurable `failure_threshold` (default 5). Once open, the breaker blocks calls to that provider until `recovery_timeout_seconds` (default 60) elapses. `ResilientExecutor` builds on this with `RetryPolicy` and `FallbackPolicy` so that a failed primary provider falls back to an alternative automatically.

## Authentication configuration

`AuthStrategy` is serializable — `to_dict` / `from_dict` and `save` / `load` persist configuration to `AUTH_STRATEGY_FILE`. The CLI surfaces this through four commands:

- `cmd_auth_setup` — interactive first-time configuration
- `cmd_auth_status` — show the current strategy
- `cmd_auth_recommend` — get a recommendation for a specific file
- `cmd_auth_reset` — clear the saved configuration

`configure_auth_interactive` drives the setup flow programmatically when you need to embed it outside the CLI.

## When this matters

You interact with this subsystem whenever you need to:

- Control which model tier handles a specific workflow stage, using `get_best_model` with `max_cost` or `max_latency_ms` constraints
- Understand why routing chose a particular model, using `get_routing_stats` over a rolling window (default 7 days)
- Switch between subscription and API authentication without changing call sites, by updating `AuthStrategy.default_mode`
- Inspect provider health, using `CircuitBreaker.get_status`
