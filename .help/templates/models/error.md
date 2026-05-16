---
type: error
name: models-error
feature: models
depth: error
generated_at: 2026-05-16T06:19:45.839514+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models errors

## Common error signatures

Failures in the `models` feature fall into three categories: authentication strategy errors, provider routing failures, and circuit breaker trips.

- **Authentication errors** — `AuthStrategy.load()` raises when the strategy file at `AUTH_STRATEGY_FILE` is missing, corrupt, or contains unrecognized field values. `configure_auth_interactive()` can fail if the file cannot be written.
- **Routing errors** — `AdaptiveModelRouter.get_best_model()` raises when no model in `MODEL_REGISTRY` meets the caller's `max_cost`, `max_latency_ms`, or `min_success_rate` constraints, or when the requested `workflow`/`stage` combination has no telemetry history.
- **Provider failures** — `AllProvidersFailedError` is raised by `ResilientExecutor` after every entry in a `FallbackPolicy` has been exhausted. Each individual attempt can fail with a provider-level exception before the circuit breaker in `CircuitBreaker` opens for that provider/tier pair.
- **Executor errors** — `EmpathyLLMExecutor.run()` propagates provider exceptions when the underlying `EmpathyLLM` call fails. Check `LLMResponse.success` (returns `False` when `content` is empty) before assuming a returned response is valid.

## Where errors originate

Authentication CLI commands are the most common entry points for user-facing failures. Routing and executor errors typically originate deeper in the stack and are reported back to CLI callers.

- `cmd_auth_setup()` — interactive first-time setup; fails if the strategy file cannot be created or if `AuthStrategy.save()` encounters a permissions error.
- `cmd_auth_status()` — reads the current strategy; fails if `AuthStrategy.load()` cannot parse an existing file.
- `cmd_auth_reset()` — clears the strategy file; fails on filesystem permission errors.
- `cmd_auth_recommend()` — calls `count_lines_of_code()` and `AuthStrategy.get_recommended_mode()`; fails if the target file does not exist or is not a valid Python file.
- `main()` — top-level CLI entry point; always returns `1` on failure.

## How to diagnose

1. **Check the exception type first.** `AllProvidersFailedError` means every fallback in the active `FallbackPolicy` was tried and failed — look at `CircuitBreaker.get_status()` to see which providers are open. A `ValueError` or `KeyError` from `AdaptiveModelRouter.get_best_model()` usually means the `workflow`/`stage` pair has no telemetry data yet.

2. **Inspect the circuit breaker state.** Call `CircuitBreaker.get_status()` to see `failure_count`, `is_open`, and `opened_at` for each provider/tier pair. A provider whose circuit is open will not be attempted until `recovery_timeout_seconds` has elapsed. Use `CircuitBreaker.reset()` to force recovery during debugging.

3. **Validate the auth strategy file.** If `AuthStrategy.load()` fails, confirm the file at `AUTH_STRATEGY_FILE` exists and contains valid JSON with all required fields (see `AuthStrategy.from_dict()`). Run `attune auth-status` to surface the parsed values, or `attune auth-reset` followed by `attune auth-setup` to rebuild the file from scratch.

4. **Check routing constraints against telemetry.** If `get_best_model()` returns no candidate, the `max_cost`, `max_latency_ms`, or `min_success_rate` thresholds may be too strict for the available `ModelPerformance` data. Call `AdaptiveModelRouter.get_routing_stats()` for the relevant `workflow` and `stage` to see actual success rates and latencies before tightening constraints.

5. **Examine `LLMResponse` fields on apparent success.** A response object can be returned without raising an exception even when the call failed — `LLMResponse.success` is `False` whenever `content` is empty. Always check this property before treating the response as valid output.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
