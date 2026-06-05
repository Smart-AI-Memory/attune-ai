---
type: comparison
name: models-comparison
feature: models
depth: comparison
generated_at: 2026-06-04T23:45:26.774404+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Comparison: Authentication modes and routing strategies in `models`

## Context

The `models` feature covers three distinct but related decisions you make when integrating LLM calls in attune:

1. **Authentication mode** — how attune authenticates with Claude (subscription vs. API key, controlled by `AuthMode` and `AuthStrategy`)
2. **Model routing** — how attune selects a model for a given task (static tier assignment vs. telemetry-driven via `AdaptiveModelRouter`)
3. **Resilience strategy** — how attune handles provider failures (direct calls vs. `CircuitBreaker` + `ResilientExecutor`)

Each axis has two or more options. The sections below help you choose.

---

## Authentication mode: `AuthMode.AUTO` vs. explicit modes

`AuthStrategy` defaults to `default_mode: AuthMode.AUTO` with `prefer_subscription: bool = True`. In AUTO mode, the strategy calls `get_recommended_mode(module_lines)` to pick between subscription and API-key auth based on the size of the file being processed.

| Factor | `AuthMode.AUTO` | Explicit mode |
|---|---|---|
| **When it applies** | Module size crosses `small_module_threshold` (500 LOC) or `medium_module_threshold` (2000 LOC) | You override `default_mode` in `AuthStrategy` |
| **Cost optimization** | Applies `cost_optimization` logic automatically | You own the cost tradeoff |
| **Token estimation** | Calls `estimate_tokens(module_lines)` using `loc_to_tokens_multiplier` (4.0) | Not used |
| **Best for** | Mixed codebases where module size varies widely | Environments where you have a fixed billing arrangement or need deterministic behavior |
| **Risk** | May switch modes unexpectedly as files grow past thresholds | Requires manual recalibration when codebase grows |

`estimate_cost(module_lines, mode)` and `get_pros_cons(module_lines)` both accept an optional `mode` argument — use them to preview the cost and tradeoff of each mode before committing.

---

## Model routing: static tier map vs. `AdaptiveModelRouter`

The registry exposes a static `TASK_TIER_MAP` that assigns every known task type to a tier (`CHEAP_TASKS`, `CAPABLE_TASKS`, `PREMIUM_TASKS`). `AdaptiveModelRouter` layers telemetry on top: it reads historical `ModelPerformance` records and re-ranks models by `quality_score` within a tier.

| Factor | Static tier map | `AdaptiveModelRouter` |
|---|---|---|
| **Selection basis** | Task type only | Task type + `success_rate`, `avg_latency_ms`, `avg_cost`, `sample_size`, `recent_failures` |
| **Cost cap** | None | `max_cost` parameter on `get_best_model()` |
| **Latency cap** | None | `max_latency_ms` parameter on `get_best_model()` |
| **Minimum quality gate** | None | `min_success_rate` (default 0.8) on `get_best_model()` |
| **Upgrade advice** | None | `recommend_tier_upgrade(workflow, stage)` returns `(bool, str)` |
| **Stats window** | N/A | `get_routing_stats(workflow, stage, days=7)` — configurable lookback |
| **Cold-start behavior** | Works immediately | Requires telemetry data; falls back to tier map when `sample_size` is low |
| **Best for** | Predictable workloads, new deployments, or when telemetry isn't yet available | Production workflows where you want cost or latency guardrails and have accumulated call history |

`AdaptiveModelRouter` is the better choice for long-running deployments. The static tier map is the right starting point — and the fallback — when telemetry is unavailable.

---

## Resilience strategy: direct execution vs. `CircuitBreaker` + `ResilientExecutor`

`EmpathyLLMExecutor` calls a provider directly. `ResilientExecutor` wraps execution with a `CircuitBreaker` that tracks per-provider failure counts and temporarily disables a provider when `failure_count` exceeds `failure_threshold` (default 5), waiting `recovery_timeout_seconds` (default 60) before allowing half-open probes (`half_open_calls`, default 1).

| Factor | Direct via `EmpathyLLMExecutor` | `CircuitBreaker` + `ResilientExecutor` |
|---|---|---|
| **Failure handling** | Raises on provider error | Opens circuit after `failure_threshold` failures; reroutes automatically |
| **Recovery** | Manual retry logic in your code | Automatic after `recovery_timeout_seconds` |
| **Fallback chain** | None built-in | `FallbackStrategy` / `FallbackPolicy` define ordered fallback steps |
| **Observability** | `LLMResponse.success`, `latency_ms`, `cost_estimate` per call | `CircuitBreaker.get_status()` shows per-provider state across calls |
| **Overhead** | Minimal | Slight per-call state check against `CircuitBreakerState` |
| **Best for** | Development, single-provider setups, or when you own retry logic externally | Production multi-provider deployments where uptime matters more than call simplicity |

---

## CLI entry points: interactive setup vs. programmatic configuration

The auth CLI provides four commands for managing `AuthStrategy`. The table below shows when each is appropriate.

| Command | Function | Best for |
|---|---|---|
| `auth setup` | `cmd_auth_setup()` | First-time configuration; calls `configure_auth_interactive()` |
| `auth status` | `cmd_auth_status()` | Auditing current strategy fields without editing |
| `auth reset` | `cmd_auth_reset()` | Wiping configuration to start over |
| `auth recommend` | `cmd_auth_recommend()` | Getting a per-file recommendation before committing to a mode |

For automation, call `get_auth_strategy()` directly; it returns the persisted `AuthStrategy` without launching an interactive prompt. Use `AuthStrategy.save()` and `AuthStrategy.load()` to manage configuration files programmatically.

---

## Use X when...

| Situation | Recommendation |
|---|---|
| You're setting up attune for the first time | Run `cmd_auth_setup()` (or `auth setup` CLI); accept `AuthMode.AUTO` defaults |
| Your modules are uniformly small (< 500 LOC) or uniformly large (> 2000 LOC) | Set `default_mode` explicitly in `AuthStrategy` — AUTO adds no value when modules don't cross thresholds |
| You've accumulated LLM call history and want cost or latency guardrails | Switch from the static tier map to `AdaptiveModelRouter.get_best_model()` with `max_cost` or `max_latency_ms` |
| You're running against a single provider in development | `EmpathyLLMExecutor` directly; skip `CircuitBreaker` overhead |
| You're running in production with multiple providers | `ResilientExecutor` with a configured `FallbackPolicy`; let `CircuitBreaker` handle transient outages |
| You want to know whether to upgrade a workflow's tier | Call `AdaptiveModelRouter.recommend_tier_upgrade(workflow, stage)` — it returns a `(bool, str)` with a human-readable reason |
| You need to inspect current routing health | Call `AdaptiveModelRouter.get_routing_stats(workflow, stage, days=7)` or `CircuitBreaker.get_status()` |
