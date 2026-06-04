---
type: note
name: models-note
feature: models
depth: note
generated_at: 2026-06-04T23:45:26.771777+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Note: models

The `models` package covers three related concerns: LLM authentication strategy, provider routing, and adaptive tier selection. These concerns are implemented across a small set of source files under `src/attune/models/`.

## Public surface

The package exports classes and top-level functions that are designed to work together.

**Classes** (defined in `adaptive_routing.py` and `auth_strategy.py`):

| Class | Purpose |
|---|---|
| `ModelPerformance` | Performance metrics for a model on a specific task — holds `success_rate`, `avg_latency_ms`, `avg_cost`, and a derived `quality_score` property |
| `AdaptiveModelRouter` | Routes tasks to models based on historical telemetry; key method is `get_best_model()` |
| `SubscriptionTier` | Enumerates Claude subscription tiers |
| `AuthMode` | Enumerates authentication mode selections (e.g., `AUTO`) |
| `AuthStrategy` | Authentication strategy configuration; persisted via `save()` / `load()` and introspected via `get_recommended_mode()` and `estimate_cost()` |

**CLI entry points** (defined in `auth_cli.py`):

| Function | Purpose |
|---|---|
| `cmd_auth_setup()` | Runs interactive authentication strategy setup |
| `cmd_auth_status()` | Shows current authentication strategy configuration |
| `cmd_auth_reset()` | Resets or clears the authentication strategy configuration |
| `cmd_auth_recommend()` | Returns an authentication recommendation for a specific file |
| `main()` | Main CLI entry point |

## How the pieces relate

The CLI functions in `auth_cli.py` and the `AuthStrategy` dataclass in `auth_strategy.py` are complementary surfaces for the same configuration state. `AuthStrategy` handles persistence and introspection programmatically; the `cmd_auth_*` functions expose the same operations interactively. `AdaptiveModelRouter` is independent of authentication — it reads telemetry to select the best model for a given workflow stage, using `ModelPerformance` records as its data source.

## Additional context

- `AuthStrategy` defaults to `SubscriptionTier.PRO`, `AuthMode.AUTO`, and `cost_optimization = True`. These defaults reflect an assumption that most users prefer subscription-based access with automatic mode selection.
- `CircuitBreaker` and `ResilientExecutor` (also exported from `__all__`) provide fault-tolerance primitives that sit between the router and the underlying LLM provider calls.
- The full list of exported names is in `__all__` across the package's source files.
