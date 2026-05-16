---
type: concept
name: models-concept
feature: models
depth: concept
generated_at: 2026-05-16T06:19:45.824442+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models

The `models` subsystem decides which LLM to call, how to authenticate, and whether to retry or fall back — so the rest of Attune can request a task type without hard-coding a provider or tier.

## Mental model

Every LLM call in Attune passes through three layers:

1. **Task classification** — a task type (for example, `user_query` or `critical_fix`) is mapped to a cost tier (`CHEAP_TASKS`, `CAPABLE_TASKS`, or `PREMIUM_TASKS`) via `TASK_TIER_MAP`.
2. **Adaptive routing** — `AdaptiveModelRouter` reads historical telemetry to pick the best concrete model for that tier, filtered by optional constraints such as `max_cost` or `max_latency_ms`.
3. **Authentication** — `AuthStrategy` determines whether to use a Claude subscription or a direct API key, based on your `SubscriptionTier` and the size of the module being processed.

These three layers operate independently, so you can change your subscription tier without touching routing logic, and routing can improve over time as telemetry accumulates without any code changes.

## Core components

### Task-to-tier mapping

`TASK_TIER_MAP` and the `CHEAP_TASKS`, `CAPABLE_TASKS`, and `PREMIUM_TASKS` constants define which capability tier each task type requires. A separate constant, `REALTIME_REQUIRED_TASKS` (which includes `user_query`, `critical_fix`, and `emergency_response`), identifies tasks that cannot tolerate queuing delays.

### Adaptive routing

`AdaptiveModelRouter` selects a model at runtime using recorded `ModelPerformance` data — each of which tracks `success_rate`, `avg_latency_ms`, `avg_cost`, and `recent_failures` for a specific model–task combination. Its `quality_score` property combines those signals into a single ranking value.

Call `get_best_model(workflow, stage)` to get the top-ranked model for a workflow stage. Pass `max_cost` or `max_latency_ms` to filter candidates. Call `recommend_tier_upgrade(workflow, stage)` when you want the router to tell you whether a higher-capability model would improve outcomes for that stage.

### Authentication strategy

`AuthStrategy` holds your authentication preferences — `subscription_tier`, `default_mode`, and thresholds such as `small_module_threshold` (500 lines) and `medium_module_threshold` (2000 lines). Given a module's line count, `get_recommended_mode()` returns the appropriate `AuthMode` (`AUTO`, or a subscription/API preference), and `estimate_cost()` computes projected spend for each mode so you can compare before committing.

`AuthStrategy` is serializable: `save()` and `load()` persist configuration to disk, and `from_dict()` / `to_dict()` round-trip through plain dictionaries.

### Circuit breaking and resilience

`CircuitBreaker` tracks per-provider failure counts. After `failure_threshold` consecutive failures, it marks that provider as unavailable for `recovery_timeout_seconds`, preventing cascading failures. `is_available(provider, tier)` is the check you call before routing; `record_success()` and `record_failure()` feed it signal. `ResilientExecutor`, `FallbackStrategy`, and `RetryPolicy` build on this to define ordered fallback chains (for example, `SONNET_TO_OPUS_FALLBACK`).

### Execution and responses

`EmpathyLLMExecutor` is the default entry point for running a task. Call `run(task_type, prompt)` and receive an `LLMResponse` — a dataclass containing `content`, `model_id`, `tier`, token counts, `cost_estimate`, and `latency_ms`. The `success` property on `LLMResponse` returns `True` when `content` is non-empty, making it safe to branch on without inspecting status codes.

`ExecutionContext` carries optional routing hints (`provider_hint`, `tier_hint`) and session metadata through the call stack without polluting function signatures.

## How the pieces fit together

```
Task type
   │
   ▼
TASK_TIER_MAP ──► tier (cheap / capable / premium)
   │
   ▼
AdaptiveModelRouter ──► model_id   ◄── ModelPerformance (telemetry)
   │
   ▼
EmpathyLLMExecutor ──► LLMResponse
   │
   ├── AuthStrategy (which credentials to use)
   └── CircuitBreaker (is this provider healthy?)
```

Telemetry written by `log_llm_call` and `log_workflow_run` feeds back into `ModelPerformance`, closing the loop so routing improves as the system accumulates real usage data.

## When this matters

- You are adding a new workflow stage and need to choose a cost tier — consult `TASK_TIER_MAP` and `get_tier_for_task()`.
- A provider is returning errors and you want to understand why calls are being skipped — check `CircuitBreaker.get_status()`.
- You want to know whether your Claude subscription is cheaper than API-key access for a given file size — call `AuthStrategy.estimate_cost()` with the file's line count.
- Routing feels stale or a model that was performing well is no longer selected — call `AdaptiveModelRouter.get_routing_stats(workflow, stage)` to inspect the last seven days of telemetry.
