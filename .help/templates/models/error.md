---
type: error
name: models-error
feature: models
depth: error
generated_at: 2026-06-04T23:45:26.754109+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models errors

## Common error signatures

Failures in the `models` feature fall into three categories: authentication strategy errors, provider routing failures, and circuit breaker trips.

**Authentication errors** occur when `AuthStrategy` cannot be loaded or saved, or when `configure_auth_interactive()` receives invalid input. Look for:

- `FileNotFoundError` — `AuthStrategy.load()` cannot find the file at the path defined by `AUTH_STRATEGY_FILE`.
- `ValueError` — `AuthStrategy.from_dict()` receives a malformed or incomplete configuration dict, or `get_recommended_mode()` receives a `module_lines` value it cannot classify.

**Provider routing errors** occur when `AdaptiveModelRouter.get_best_model()` cannot find a model that satisfies the given constraints (`max_cost`, `max_latency_ms`, `min_success_rate`). This typically means no `ModelPerformance` entry in the telemetry store meets all three thresholds simultaneously.

**Circuit breaker trips** are raised by `CircuitBreaker` when `CircuitBreakerState.is_open` is `True` for a provider. `AllProvidersFailedError` indicates that every configured provider's circuit breaker is open and no fallback remains in the `FallbackStrategy`.

## Where errors originate

The following CLI entry points are the most common places where upstream callers first observe a failure:

- `cmd_auth_setup()` — interactive setup; fails if the target path is not writable or if the user provides input that cannot be parsed into a valid `AuthStrategy`.
- `cmd_auth_status()` — reads the saved strategy; fails with `FileNotFoundError` if setup has not been completed (`AuthStrategy.setup_completed` is `False` or the file is absent).
- `cmd_auth_reset()` — deletes the saved strategy; fails if the file cannot be removed.
- `cmd_auth_recommend()` — calls `count_lines_of_code()` then `get_recommended_mode()`; fails if the target file path does not exist or is not a valid Python file.
- `main()` — the top-level CLI entry point; returns exit code `1` on any unhandled error from the above commands.

Errors that originate deeper in routing or circuit-breaker logic (for example, inside `EmpathyLLMExecutor.run()`) propagate up through these commands, so the CLI exit code and stderr output are usually the first visible symptom.

## How to diagnose

1. **Read the exit code and stderr together.** `main()` returns `1` on failure. The stderr output names the exception type and message, which tells you which category — auth, routing, or circuit breaker — you are dealing with.

2. **Check `CircuitBreaker.get_status()`.** If you see `AllProvidersFailedError`, call `get_status()` to inspect each provider's `CircuitBreakerState`. A state with `is_open: True` and a recent `opened_at` timestamp means the provider hit `failure_threshold` consecutive failures. Use `CircuitBreaker.reset()` to manually clear a specific provider while you investigate.

3. **Inspect `ModelPerformance` fields for routing failures.** When `get_best_model()` fails to return a model, check the `success_rate`, `avg_latency_ms`, and `avg_cost` fields on the relevant `ModelPerformance` records. Compare them against the constraints you passed. A high `recent_failures` count alongside a low `success_rate` means the model has degraded and no longer clears the default `min_success_rate` of `0.8`.

4. **Verify the auth strategy file.** Run `cmd_auth_status()` to confirm `setup_completed` is `True` and the strategy loaded from `AUTH_STRATEGY_FILE` is valid. If it is missing or corrupt, run `cmd_auth_setup()` to regenerate it, or call `AuthStrategy.load()` directly and inspect the returned object's fields.

5. **Check `recommend_tier_upgrade()` output.** If routing consistently fails for a `(workflow, stage)` pair, call `AdaptiveModelRouter.recommend_tier_upgrade()`. A `True` return value means historical telemetry shows the current `SubscriptionTier` is insufficient for the workload.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
