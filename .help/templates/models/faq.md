---
type: faq
name: models-faq
feature: models
depth: faq
generated_at: 2026-05-16T06:19:45.849980+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Models FAQ

## What does the models feature do?

It provides a unified registry and routing layer for LLM providers. Specifically, it handles authentication strategy configuration, adaptive model routing based on historical telemetry, circuit breaking for failing providers, and cost estimation across subscription tiers.

## When do I need models versus something else?

Use models when your code needs to select a model, authenticate with a provider, estimate costs, or recover from provider failures. If you only need to call an LLM directly without any routing or auth logic, check `.help/features.yaml` to see whether a simpler feature covers your use case.

## What are the main entry points?

For CLI use, start with the `cmd_auth_*` functions in `src/attune/models/auth_cli.py`:

- `cmd_auth_setup()` — runs interactive first-time authentication setup
- `cmd_auth_status()` — shows the current authentication strategy configuration
- `cmd_auth_reset()` — clears the saved authentication strategy
- `cmd_auth_recommend(args)` — recommends an auth mode for a specific file based on its line count

For programmatic use, `get_auth_strategy()` returns the global `AuthStrategy` instance, and `EmpathyLLMExecutor` is the default executor that wraps routing and provider calls together.

## How does adaptive routing work?

`AdaptiveModelRouter` reads historical telemetry to pick the best model for a given workflow and stage. You can pass `max_cost`, `max_latency_ms`, and `min_success_rate` constraints to `get_best_model()` to narrow the selection. Routing stats are available via `get_routing_stats()`.

## What happens when a provider fails?

`CircuitBreaker` tracks failures per provider and tier. After `failure_threshold` failures (default: 5), it marks the provider unavailable for `recovery_timeout_seconds` (default: 60). Call `is_available()` before routing to a provider, and use `record_success()` / `record_failure()` to keep the state current. You can inspect all provider states with `get_status()` or reset a specific provider with `reset()`.

## How does the auth strategy decide which mode to use?

`AuthStrategy.get_recommended_mode()` takes a module's line count and compares it against `small_module_threshold` (default: 500 lines) and `medium_module_threshold` (default: 2000 lines) to return an `AuthMode`. Use `estimate_cost()` and `get_pros_cons()` on the same instance to evaluate the tradeoff before committing to a mode.

## How do I debug a routing or auth failure?

Run `pytest -k "models" -v` first. If the tests pass but your code still fails:

1. Call `cmd_auth_status()` (or `get_auth_strategy()`) to confirm the active configuration.
2. Call `CircuitBreaker.get_status()` to check whether a provider is currently open.
3. Add a `logger.debug` statement at the suspected failure point and re-run with logging enabled.

For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where are the source files?

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
