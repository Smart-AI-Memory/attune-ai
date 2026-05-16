---
type: comparison
name: models-comparison
feature: models
depth: comparison
generated_at: 2026-05-16T06:19:45.859347+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Comparison: Models feature — authentication modes and routing strategies

## Context

The `models` feature covers three distinct but related responsibilities: authenticating against LLM providers (Claude subscription vs. API key), routing tasks to the right model tier based on telemetry, and managing circuit breakers when providers fail. Understanding the tradeoffs within this feature helps you configure it correctly for your workload.

## Authentication mode comparison

`AuthStrategy` supports two authentication modes, selected via `AuthMode`. The system defaults to `AuthMode.AUTO`, which picks a mode based on module size.

| Factor | Subscription mode (`prefer_subscription=True`) | API key mode (`prefer_subscription=False`) |
|---|---|---|
| **Cost model** | Flat subscription fee; no per-token charge | Pay-per-token; cost scales with usage |
| **Best for** | High-volume, continuous workflows | Sporadic or exploratory use |
| **Token estimation** | `estimate_tokens()` uses `loc_to_tokens_multiplier=4.0` | Same estimation; cost calculated differently via `estimate_cost()` |
| **Small modules (<500 LOC)** | May be cost-inefficient | Generally cheaper |
| **Large modules (>2000 LOC)** | Cost advantage grows with volume | Costs accumulate quickly |
| **Setup** | `cmd_auth_setup()` interactive wizard | `cmd_auth_setup()` interactive wizard |
| **Switching** | `cmd_auth_reset()` then re-run setup | `cmd_auth_reset()` then re-run setup |

`AuthStrategy.get_recommended_mode()` encodes this logic: pass your module's line count and it returns the optimal `AuthMode` for that size category (`get_module_size_category()` returns `'small'`, `'medium'`, or `'large'`).

## Model tier comparison

The registry maps tasks to three tiers. `TASK_TIER_MAP` and `AdaptiveModelRouter` use these distinctions to select models at runtime.

| Tier | Task examples | Latency expectation | Cost expectation | When the router selects it |
|---|---|---|---|---|
| **Cheap** (`CHEAP_TASKS`) | Background analysis, batch summarization | Higher acceptable | Lowest | `max_cost` constraint set, `success_rate ≥ 0.8` on telemetry |
| **Capable** (`CAPABLE_TASKS`) | Code generation, test writing | Moderate | Moderate | Default for most workflow stages |
| **Premium** (`PREMIUM_TASKS`) | Complex reasoning, architecture review | Lowest acceptable | Highest | `recommend_tier_upgrade()` returns `True` based on historical failure rates |
| **Realtime** (`REALTIME_REQUIRED_TASKS`) | `chat`, `live_coding`, `security_incident`, `emergency_response` | Must be minimal | Varies | Task type is in the frozenset; cannot be overridden by cost constraints |

The router scores candidates using `ModelPerformance.quality_score`, which combines `success_rate`, `avg_latency_ms`, and `avg_cost`. You can constrain selection with `max_cost`, `max_latency_ms`, and `min_success_rate` parameters on `get_best_model()`.

## Routing strategy comparison

`AdaptiveModelRouter` and direct model selection via the registry represent two different approaches.

| Aspect | `AdaptiveModelRouter` | Direct registry lookup (`get_model()`, `get_tier_for_task()`) |
|---|---|---|
| **Selection basis** | Live telemetry over a configurable window (default 7 days) | Static registry configuration |
| **Adapts to failures** | Yes — `recent_failures` and `sample_size` factor into `quality_score` | No — returns the registered model regardless of runtime behavior |
| **Circuit breaker integration** | Works alongside `CircuitBreaker`; failing providers are excluded | Not integrated; caller is responsible |
| **Best for** | Production workflows where model reliability varies | Testing, scripting, or when you need deterministic model selection |
| **Upgrade recommendations** | `recommend_tier_upgrade()` signals when a higher tier would improve outcomes | Not available |
| **Observability** | `get_routing_stats(workflow, stage, days=7)` returns structured performance data | None built in |

## Circuit breaker behavior

`CircuitBreaker` sits between `EmpathyLLMExecutor` and the provider. It opens after `failure_threshold` failures (default: 5) and stays open for `recovery_timeout_seconds` (default: 60). During the half-open state, `half_open_calls` (default: 1) probe call is allowed before fully re-enabling the provider.

If you call providers directly without going through `EmpathyLLMExecutor`, the circuit breaker does not apply — you are responsible for handling provider failures.

## CLI entry points

| Command function | Purpose | Use when |
|---|---|---|
| `cmd_auth_setup()` | Interactive first-time configuration | Setting up a new environment |
| `cmd_auth_status()` | Display current `AuthStrategy` fields | Debugging unexpected auth behavior |
| `cmd_auth_reset()` | Clear saved strategy from disk | Switching providers or subscription tiers |
| `cmd_auth_recommend(args)` | Score a specific file and return the recommended `AuthMode` | Deciding auth mode for a single large module |

## Use X when...

**Use `AuthMode.AUTO` with `prefer_subscription=True`** when you run continuous workflows against large codebases (>2000 LOC per module). The subscription tier amortizes cost across high token volumes, and `get_recommended_mode()` will select it automatically.

**Use API key mode** when your usage is infrequent or you are running one-off scripts. Token costs stay low when volume is low, and you avoid paying for subscription capacity you do not use.

**Use `AdaptiveModelRouter`** in any production workflow. It is the better default: it reacts to real failure rates, avoids degraded providers automatically, and surfaces upgrade recommendations before failures compound.

**Use direct registry lookup** only in tests or throwaway scripts where you need a fixed, predictable model and do not want telemetry to influence selection.

**Use the `REALTIME_REQUIRED_TASKS` path** for anything user-facing or time-critical (`chat`, `live_coding`, `security_incident`, `emergency_response`). Cost constraints passed to `get_best_model()` are not applied to these tasks — latency takes priority unconditionally.

**Do not use this feature directly** if your workflow spans multiple providers and you need coordinated fallback logic. The `ResilientExecutor` and `FallbackStrategy` layer above `models` handles multi-provider orchestration; wiring `AdaptiveModelRouter` and `CircuitBreaker` together manually duplicates logic that already exists there.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
