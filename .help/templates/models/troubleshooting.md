---
type: troubleshooting
name: models-troubleshooting
feature: models
depth: troubleshooting
generated_at: 2026-06-04T23:45:26.762570+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Troubleshoot models

## Before you start

The `models` feature covers the Unified Model Registry, adaptive model routing via `AdaptiveModelRouter`, circuit breaker logic via `CircuitBreaker`, and authentication strategy management via `AuthStrategy`. Issues typically fall into one of three areas: authentication configuration, model routing and tier selection, or provider failures tripped by the circuit breaker.

## Symptom table

| If you observe | Check |
|---|---|
| `cmd_auth_setup` fails or exits non-zero | Run `cmd_auth_status` to see what the current `AuthStrategy` configuration holds — a missing or corrupt `AUTH_STRATEGY_FILE` is the most common cause |
| Wrong model selected for a task | Inspect `AdaptiveModelRouter.get_routing_stats(workflow, stage)` — low `sample_size` or high `recent_failures` in `ModelPerformance` skews selection |
| A provider is never called despite being configured | Call `CircuitBreaker.get_status()` — `is_open: true` on a provider means it tripped; check `failure_count` and `opened_at` |
| `get_best_model` raises or returns an unexpected model | Verify that `min_success_rate`, `max_cost`, and `max_latency_ms` constraints aren't filtering out all candidates |
| Cost or latency estimates look wrong | Check `ModelPerformance.avg_cost`, `avg_latency_ms`, and `quality_score` for the affected `model_id` and `tier` |
| `AuthStrategy.get_recommended_mode` returns an unexpected `AuthMode` | Confirm `small_module_threshold` and `medium_module_threshold` match your repo's actual line counts; use `count_lines_of_code(file_path)` to measure |
| `LLMResponse.success` is `False` | Inspect `LLMResponse.content` (empty string signals failure) and `LLMResponse.metadata` for provider error details |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows it.

### 1. Check authentication status

```bash
python -m attune.models auth status
```

This calls `cmd_auth_status` and prints the active `AuthStrategy` fields (`subscription_tier`, `default_mode`, `setup_completed`, etc.). If `setup_completed` is `False`, run setup before investigating anything else:

```bash
python -m attune.models auth setup
```

### 2. Inspect the model registry

```python
from attune.models import print_registry
print_registry(format='table')          # all providers
print_registry(provider='anthropic')    # one provider
```

Confirm that the model IDs and tiers you expect are present. A missing entry means the registry (`MODEL_REGISTRY`, `TASK_TIER_MAP`) doesn't include that model or task type.

### 3. Check routing stats and circuit breaker state

```python
from attune.models import AdaptiveModelRouter, CircuitBreaker

# Replace with a real telemetry store instance
router = AdaptiveModelRouter(telemetry=telemetry_store)
print(router.get_routing_stats(workflow='my_workflow', stage='my_stage', days=7))

cb = CircuitBreaker()
print(cb.get_status())   # shows failure_count, is_open, opened_at per provider
```

If a circuit breaker is open, reset it after the underlying provider issue is resolved:

```python
cb.reset(provider='anthropic')          # reset one provider
cb.reset()                              # reset all
```

### 4. Verify `get_best_model` constraints

If `AdaptiveModelRouter.get_best_model` returns an unexpected model or raises, check whether your constraint arguments are too strict:

```python
model = router.get_best_model(
    workflow='my_workflow',
    stage='my_stage',
    max_cost=0.01,          # None = no limit
    max_latency_ms=5000,    # None = no limit
    min_success_rate=0.8,   # default
)
```

Relax one constraint at a time to identify which filter is eliminating all candidates.

### 5. Check tier upgrade recommendations

```python
should_upgrade, reason = router.recommend_tier_upgrade(
    workflow='my_workflow',
    stage='my_stage',
)
print(should_upgrade, reason)
```

If the router recommends an upgrade, `ModelPerformance.quality_score` for the current tier is likely below the threshold needed to keep routing to it.

### 6. Run the related tests

```bash
pytest -k "models" -v
```

A failing test that exercises the same code path will often expose the root cause faster than manual inspection.

## Common fixes

**Circuit breaker is open — provider calls are blocked**

Call `CircuitBreaker.reset(provider='<name>')` after confirming the provider is healthy. The breaker opens after `failure_threshold` consecutive failures (default: 5) and stays open for `recovery_timeout_seconds` (default: 60 s).

**Authentication strategy file is missing or corrupt**

Delete the file at the path returned by `AUTH_STRATEGY_FILE` and re-run setup:

```bash
python -m attune.models auth reset
python -m attune.models auth setup
```

**`AuthStrategy` thresholds don't match your codebase**

`get_recommended_mode` uses `small_module_threshold` (default: 500 lines) and `medium_module_threshold` (default: 2000 lines). If your modules are larger, update those fields and save:

```python
from attune.models import get_auth_strategy
strategy = get_auth_strategy()
strategy.medium_module_threshold = 5000
strategy.save()
```

**`min_success_rate` filters out all models**

The default `min_success_rate=0.8` in `get_best_model` can exclude every candidate if telemetry is sparse (`sample_size` is small). Lower the threshold temporarily or clear stale telemetry records so the router can rebuild baselines.

**Dependency version mismatch causes unexpected behavior**

The `EmpathyLLMExecutor` wraps an external `EmpathyLLM` instance. If behavior changed after a dependency update, confirm the installed version:

```bash
pip show empathy-llm    # adjust package name to match your environment
```

**`LLMResponse.success` is `False` intermittently**

`success` returns `True` only when `content` is a non-empty string. Intermittent failures often indicate provider rate limits or transient network errors. Check `LLMResponse.metadata` for provider-side error codes, then confirm `CircuitBreaker.is_available(provider, tier)` before retrying.

## Source files

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 47 (code fence) | error | `from attune.models import print_registry` — `print_registry` not found in `attune.models` |
