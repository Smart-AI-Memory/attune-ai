---
type: warning
name: models-warning
feature: models
depth: warning
generated_at: 2026-05-16T06:19:45.845318+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models cautions

## What to watch for

The `models` feature spans LLM authentication, adaptive model routing, circuit breaking, and telemetry. The risks below reflect the areas where misconfiguration or missed edge cases produce failures that are hard to trace after the fact.

## Risk areas

### `cmd_auth_reset()` silently discards your `AuthStrategy`

`cmd_auth_reset()` clears the saved authentication strategy file at `AUTH_STRATEGY_FILE`. If you call it programmatically — or a user runs it from the CLI — all customized fields (`subscription_tier`, `small_module_threshold`, `loc_to_tokens_multiplier`, and so on) are lost without a confirmation prompt in non-interactive contexts. Back up or serialize the current strategy via `AuthStrategy.to_dict()` before invoking a reset.

### `AdaptiveModelRouter.get_best_model()` falls back silently when no model meets your constraints

When you pass `max_cost`, `max_latency_ms`, or `min_success_rate` to `get_best_model()`, the router filters against `ModelPerformance` telemetry. If no recorded model meets all constraints, the method still returns a model — it does not raise. Low `sample_size` values on a `ModelPerformance` record mean the `quality_score` and `success_rate` fields are statistically weak, so routing decisions made early in a workflow's lifetime may not reflect real performance. Check `get_routing_stats()` before tightening constraint values in production.

### Circuit breaker state is per-process and resets on restart

`CircuitBreaker` tracks `CircuitBreakerState` (failure count, `is_open`, `opened_at`) in memory. A provider that tripped the breaker in one process appears healthy to any new process or worker. In multi-process or containerized deployments, a provider can be simultaneously open in one worker and closed in another. If you need consistent circuit state across workers, you must persist and share it externally — the current implementation has no built-in backend for this.

### `AuthStrategy.get_recommended_mode()` uses line-count thresholds that may not match your modules

`get_recommended_mode()` categorizes a module as small, medium, or large based on `small_module_threshold` (default 500 lines) and `medium_module_threshold` (default 2000 lines), then recommends an `AuthMode`. Generated files, data files checked in as `.py`, or auto-formatted files can have artificially high line counts. Run `count_lines_of_code()` on the specific file before accepting the recommendation at face value, and adjust the thresholds in your saved `AuthStrategy` if the defaults misclassify your modules.

### `EmpathyLLMExecutor` telemetry is only recorded if a `TelemetryBackend` is provided at construction

`EmpathyLLMExecutor.__init__()` accepts an optional `telemetry_store`. If you construct the executor without one, calls still succeed, but no `LLMCallRecord` is written. `AdaptiveModelRouter` depends on telemetry to rank models; an executor running without a store silently starves the router of signal. Always pass a `telemetry_store` in production configurations, and verify with `get_routing_stats()` that records are accumulating.

## How to avoid problems

1. **Serialize `AuthStrategy` before any reset.** Call `AuthStrategy.to_dict()` and store the result before running `cmd_auth_reset()` or any code path that may call it transitively.

2. **Warm up telemetry before tightening routing constraints.** Use `get_routing_stats(workflow, stage, days=7)` to confirm you have a meaningful `sample_size` before setting strict `max_cost` or `min_success_rate` values in `get_best_model()`.

3. **Always construct `EmpathyLLMExecutor` with a `telemetry_store` in production.** Without it, the adaptive router receives no feedback and defaults to static tier assignments.

4. **Do not share `CircuitBreaker` instances across process boundaries.** Treat each instance as local to its process and design your deployment to tolerate divergent breaker states between workers.

5. **Depend only on the public API.** Names listed in `__all__` are stable. Private helpers (names starting with `_`) can change without notice across refactors.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
