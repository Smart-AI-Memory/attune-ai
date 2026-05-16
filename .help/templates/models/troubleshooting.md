---
type: troubleshooting
name: models-troubleshooting
feature: models
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.847567+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Troubleshoot models

## Before you start

The `models` feature covers three interconnected concerns: LLM authentication strategy (`AuthStrategy`), adaptive model routing (`AdaptiveModelRouter`), and provider circuit-breaking (`CircuitBreaker`). A failure in any one of these can surface as a misrouted task, an unexpected provider error, or a silent wrong result.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Wrong model selected for a task | `AdaptiveModelRouter.get_best_model()` — inspect the `workflow`, `stage`, and `max_cost`/`max_latency_ms` constraints you are passing |
| All requests routed to a single provider | `CircuitBreaker.get_status()` — one or more providers may have an open circuit (`is_open: true`) |
| `LLMResponse.success` is `False` or `content` is empty | Check `LLMResponse.model_id`, `provider`, and `latency_ms` — the executor may have hit a timeout or received an empty payload |
| Cost or token estimates look wrong | `AuthStrategy.estimate_cost()` and `estimate_tokens()` — verify `loc_to_tokens_multiplier` (default `4.0`) and that `subscription_tier` matches your actual plan |
| Auth setup appears complete but routing uses wrong mode | `cmd_auth_status` — confirm `setup_completed: true` and `default_mode` in the saved strategy file (`AUTH_STRATEGY_FILE`) |
| Intermittent failures on one provider | `CircuitBreaker` state — check `failure_count` and `last_failure`; the breaker opens after 5 failures and stays open for 60 seconds by default |
| `get_best_model()` raises or returns unexpected fallback | Telemetry store may lack sufficient samples — `ModelPerformance.sample_size` below threshold causes the router to fall back to defaults |

## Step-by-step diagnosis

1. **Reproduce the failure in isolation.**
   Strip the call to its required arguments. For routing issues, call `AdaptiveModelRouter.get_best_model(workflow, stage)` directly. For auth issues, call `get_auth_strategy()` and print the result. Confirm the failure occurs outside the surrounding workflow before going deeper.

2. **Check circuit-breaker state.**
   Call `CircuitBreaker.get_status()` and look for any provider where `is_open` is `True`. An open circuit silently redirects all traffic away from that provider:

   ```python
   from attune.models import CircuitBreaker
   cb = CircuitBreaker()
   print(cb.get_status())
   ```

   To reset a tripped breaker manually:

   ```python
   cb.reset(provider="anthropic")   # reset one provider
   cb.reset()                        # reset all providers
   ```

3. **Inspect the auth strategy on disk.**
   Run the CLI to see exactly what the saved strategy contains:

   ```
   attune auth status
   ```

   Or call `cmd_auth_status` directly. If `setup_completed` is `False` or the file is missing, re-run interactive setup:

   ```
   attune auth setup
   ```

4. **Check routing telemetry.**
   Call `AdaptiveModelRouter.get_routing_stats(workflow, stage, days=7)` to see what the router knows about recent performance. If `sample_size` is 0 or very low, the router has no signal and falls back to tier defaults — this is expected behavior, not a bug.

5. **Enable DEBUG logging and re-run.**
   Set the log level before executing the failing call:

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

   The executor logs model selection, latency, and cost estimates at DEBUG level. This often reveals which routing constraint (`max_cost`, `max_latency_ms`, or `min_success_rate`) is eliminating candidates.

6. **Run the related tests.**
   ```
   pytest -k "models" -v
   ```
   If a test covers the failing path, run it in isolation first. Passing tests confirm that the core logic is intact and the issue is likely in configuration or environment.

## Common fixes

- **Open circuit breaker blocking a provider.**
  Call `CircuitBreaker.reset(provider="<name>")` to re-enable the provider immediately. If it trips again quickly, the underlying provider is genuinely unhealthy — check API status or rotate credentials.

- **Auth strategy file missing or corrupt.**
  Delete the file at `AUTH_STRATEGY_FILE` and re-run setup:
  ```
  attune auth reset
  attune auth setup
  ```

- **Wrong subscription tier configured.**
  If `AuthStrategy.subscription_tier` does not match your actual Claude plan, cost estimates and mode recommendations will be wrong. Update via `attune auth setup` or edit the strategy file and reload with `AuthStrategy.load()`.

- **`get_best_model()` ignores a preferred model due to cost constraint.**
  Lower or remove the `max_cost` argument to confirm the constraint is the cause. If the constraint is intentional, call `AdaptiveModelRouter.recommend_tier_upgrade(workflow, stage)` to see whether a tier upgrade would unblock routing.

- **`min_success_rate` too high for available telemetry.**
  The default is `0.8`. If your telemetry store is new or sparse, no model may meet this threshold. Pass a lower value explicitly until enough samples accumulate:
  ```python
  router.get_best_model(workflow, stage, min_success_rate=0.5)
  ```

- **Dependency version mismatch.**
  A `pip` upgrade can change provider client behavior. Confirm installed versions with:
  ```
  pip show anthropic
  ```
  This change is outside the `models` feature itself — pin the version in your requirements file if the mismatch caused a regression.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
