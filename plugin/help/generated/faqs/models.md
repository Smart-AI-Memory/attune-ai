---
name: models
source: content/features/models.md
tags:
- models
- auth
- llm
type: faq
---

# Models FAQ

## What does the models feature do?

It provides a unified registry for LLM providers, adaptive routing based on historical telemetry, and authentication strategy management — including support for Claude subscription tiers versus direct API access.

## When do I need the models feature?

Use it when your code needs to select or call an LLM. Specifically, it covers:

- Routing a task to the best-performing model with `AdaptiveModelRouter.get_best_model()`
- Configuring how the system authenticates with a provider via `AuthStrategy`
- Running LLM tasks through a standardized executor with `EmpathyLLMExecutor`
- Inspecting the model registry with `print_registry()`

If you only need telemetry records, look at `TelemetryStore` and `log_llm_call()` instead — those live in the telemetry module.

## What are the main entry points?

For interactive or CLI-driven work:

- `cmd_auth_setup(args)` — runs the interactive authentication setup wizard
- `cmd_auth_status(args)` — prints the current authentication strategy configuration
- `cmd_auth_reset(args)` — clears a saved authentication strategy
- `cmd_auth_recommend(args)` — recommends an auth mode for a specific file
- `configure_auth_interactive(module_lines)` — programmatic first-time setup

For routing and execution:

- `AdaptiveModelRouter.get_best_model(workflow, stage)` — returns the best model ID for a workflow/stage pair, with optional `max_cost`, `max_latency_ms`, and `min_success_rate` filters
- `EmpathyLLMExecutor.run(task_type, prompt)` — executes a prompt and returns an `LLMResponse`

## How does adaptive routing decide which model to use?

`AdaptiveModelRouter` queries historical telemetry — stored as `ModelPerformance` records — and ranks candidates by their `quality_score` property. You can constrain the result with `max_cost`, `max_latency_ms`, and `min_success_rate` (default `0.8`). Call `get_routing_stats(workflow, stage)` to see what telemetry the router is working from.

## What is a circuit breaker, and when does it activate?

`CircuitBreaker` temporarily marks a provider unavailable after it reaches `failure_threshold` consecutive failures (default `5`). It reopens for a probe call after `recovery_timeout_seconds` (default `60`). You can check provider status with `CircuitBreaker.get_status()` or manually reset it with `CircuitBreaker.reset()`.

## How do I check whether a response succeeded?

Inspect the `success` property on `LLMResponse` — it returns `True` when the response has non-empty content. You can also check `total_tokens` (the sum of `tokens_input` and `tokens_output`) and `cost_estimate` for cost accounting.

## How does authentication strategy pick a mode for my file?

Call `AuthStrategy.get_recommended_mode(module_lines)`. It uses `small_module_threshold` (default `500` lines) and `medium_module_threshold` (default `2000` lines) to categorize the file, then factors in `prefer_subscription` and `cost_optimization` settings to return an `AuthMode`. Use `estimate_cost(module_lines)` to see the projected cost before committing.

## How do I debug a routing or execution failure?

Run `pytest -k "models" -v` first. If the tests pass but your code still fails:

1. Call `AdaptiveModelRouter.get_routing_stats(workflow, stage)` to confirm the router has sufficient telemetry (check `sample_size` on the relevant `ModelPerformance` record).
2. Call `CircuitBreaker.get_status()` to check whether a provider is currently open.
3. Call `cmd_auth_status(args)` to verify the active authentication strategy.
4. Add a `logger.debug` call around your `EmpathyLLMExecutor.run()` invocation and re-run with logging enabled.

## Where are the source files?

All source files live under `src/attune/models/`.

**Tags:** `models`, `auth`, `llm`
