---
type: warning
name: models-warning
feature: models
depth: warning
generated_at: 2026-06-04T23:45:26.760258+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models cautions

## What to watch for

The `models` feature spans LLM authentication strategy management, adaptive provider routing, and circuit-breaker resilience. The risks below apply whether you are calling the Python API directly or using the CLI commands in `src/attune/models/auth_cli.py`.

## Risk areas

### `cmd_auth_reset()` permanently clears your stored strategy

`cmd_auth_reset()` deletes the file at `AUTH_STRATEGY_FILE`. There is no confirmation prompt. Running it in a shared or CI environment removes the strategy for every process that calls `get_auth_strategy()`, causing them to fall back to defaults (`AuthMode.AUTO`, `SubscriptionTier.PRO`, `prefer_subscription=True`). Run `cmd_auth_status()` first to record the current configuration if you may need to restore it.

### `AdaptiveModelRouter.get_best_model()` silently falls back when filters are too strict

`get_best_model()` accepts `max_cost`, `max_latency_ms`, and `min_success_rate` filters. If no model in telemetry satisfies all three constraints, the router returns a fallback rather than raising an error. A `min_success_rate` of `0.8` (the default) combined with a tight `max_cost` can silently route tasks to a lower-quality model. Call `get_routing_stats(workflow, stage)` after tightening constraints to verify the model being selected is the one you expect.

### `CircuitBreaker` state is not persisted across process restarts

`CircuitBreakerState` holds `failure_count`, `last_failure`, `is_open`, and `opened_at` in memory only. When a process restarts — including test runners that spawn subprocesses — the circuit breaker resets to closed regardless of recent provider failures. A provider that was open at shutdown will receive requests immediately on restart. If you need persistent open/closed state, serialize it yourself via `CircuitBreaker.get_status()` and restore it before traffic resumes.

### `AuthStrategy.loc_to_tokens_multiplier` drives cost estimates; the default may not fit your codebase

`estimate_cost()` and `estimate_tokens()` both multiply lines of code by `loc_to_tokens_multiplier` (default `4.0`). Codebases with dense imports, long strings, or generated code can have actual token-to-line ratios well above 4.0, causing cost estimates returned to callers to be understated. Calibrate this field against a representative sample before relying on `estimate_cost()` for budget decisions.

### `LLMResponse` compatibility aliases mask field renames

`LLMResponse` exposes `input_tokens`, `output_tokens`, `model_used`, and `cost` as read-only properties that alias `tokens_input`, `tokens_output`, `model_id`, and `cost_estimate` respectively. Code that writes to the alias names (e.g., `response.cost = 0`) will not update the underlying field. Always read and write using the canonical field names (`tokens_input`, `tokens_output`, `model_id`, `cost_estimate`) to avoid silent no-ops.

### `cmd_auth_recommend()` result depends on the file's line count at call time

`cmd_auth_recommend()` calls `count_lines_of_code()` on the target file and passes the result to `AuthStrategy.get_recommended_mode()`, which applies the `small_module_threshold` (default 500 lines) and `medium_module_threshold` (default 2000 lines) breakpoints. If the file is mid-edit when you run the recommendation, the line count — and therefore the recommendation — reflects the unsaved state. Save the file before calling `cmd_auth_recommend()` for a stable result.

## How to avoid problems

1. **Verify routing decisions with `get_routing_stats()`** before deploying constraint changes to `get_best_model()`. The method accepts `workflow`, an optional `stage`, and a `days` lookback window, and returns the full distribution of model selections.

2. **Snapshot `CircuitBreaker.get_status()` in integration tests** that exercise failure paths. Compare the snapshot before and after to confirm the breaker opens and closes as expected, rather than relying on in-memory state that resets between test sessions.

3. **Use the canonical `AuthStrategy` fields** (`small_module_threshold`, `medium_module_threshold`, `loc_to_tokens_multiplier`) when serializing and deserializing via `to_dict()` / `from_dict()`. The compatibility properties on `LLMResponse` are read aliases, not writeable fields.

4. **Treat `AUTH_STRATEGY_FILE` as shared state** in multi-process setups. `AuthStrategy.save()` and `AuthStrategy.load()` both operate on the same path; concurrent writes are not coordinated.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
