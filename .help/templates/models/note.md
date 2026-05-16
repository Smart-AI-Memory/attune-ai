---
type: note
name: models-note
feature: models
depth: note
generated_at: 2026-05-16T06:19:45.856870+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Note: models

## Context

The `models` package handles three related concerns: authenticating with LLM providers, selecting the right model tier for a given task, and routing requests based on historical telemetry. These concerns are spread across four source files under `src/attune/models/`.

## Package boundary

The package exposes two kinds of public symbols.

**Classes** (defined in `adaptive_routing.py` and `auth_strategy.py`):

| Class | File | Purpose |
|---|---|---|
| `ModelPerformance` | `adaptive_routing.py` | Holds per-task performance metrics: success rate, latency, cost, and a computed `quality_score` |
| `AdaptiveModelRouter` | `adaptive_routing.py` | Selects the best model for a workflow stage using telemetry; supports cost and latency caps |
| `SubscriptionTier` | `auth_strategy.py` | Enumerates Claude subscription tiers |
| `AuthMode` | `auth_strategy.py` | Enumerates authentication mode options |
| `AuthStrategy` | `auth_strategy.py` | Stores and persists the active authentication configuration |

**CLI entry points** (defined in `auth_cli.py`):

| Function | Purpose |
|---|---|
| `cmd_auth_setup()` | Interactive first-time setup |
| `cmd_auth_status()` | Displays current strategy configuration |
| `cmd_auth_reset()` | Clears saved configuration |
| `cmd_auth_recommend()` | Recommends an auth mode for a specific file |
| `main()` | CLI entry point |

## Design relationship

The CLI functions and the `AuthStrategy` class are designed to compose. `AuthStrategy` owns the data model and persistence (`save()` / `load()`), while the `cmd_auth_*` functions in `auth_cli.py` wrap it for interactive use. Similarly, `AdaptiveModelRouter` consumes `ModelPerformance` records produced by the telemetry layer to make routing decisions.

The package also includes resilience infrastructure (`CircuitBreaker`, `ResilientExecutor`) and a standardized response envelope (`LLMResponse`) that all executors return, making provider-switching transparent to callers.

## Source files

- `src/attune/models/adaptive_routing.py`
- `src/attune/models/auth_strategy.py`
- `src/attune/models/auth_cli.py`

**Tags:** `models`, `auth`, `llm`
