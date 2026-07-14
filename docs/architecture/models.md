# Models

## Overview

The models subsystem decides **which** model runs a task, **how** it
authenticates, and **what** it costs. It is the cost-optimization core:
every task is classified into a tier (`CHEAP`, `CAPABLE`, `PREMIUM`),
each tier maps to a concrete model in a registry, and an auth strategy
chooses between your Claude subscription and the Anthropic API per call.

It owns three concerns: the **registry** (models, tiers, pricing), the
**router** (task → tier → model selection, including adaptive routing
from telemetry), and **auth/provider configuration** (subscription vs
API, persisted to `~/.attune/`).

It is **not** responsible for executing workflows, tracking
cross-session telemetry beyond routing stats, or managing memory —
those live in their own subsystems. You touch the models layer when you
need to know why a task picked a given model, change provider/auth, or
read pricing for a cost estimate.

Two CLI namespaces front this subsystem: `attune auth` (authentication
strategy) and `attune provider` (provider selection). The Python API
under `attune.models` is the programmatic equivalent.

## Concepts

Three ideas compose the whole subsystem:

1. **Tiers** — `ModelTier` is a three-value enum (`CHEAP`, `CAPABLE`,
   `PREMIUM`). Every task type maps to exactly one tier via
   `TASK_TIER_MAP`; unknown tasks default to `CAPABLE`.
2. **Registry** — `MODEL_REGISTRY` is a nested
   `dict[str, dict[str, ModelInfo]]` keyed by provider then tier. Each
   `ModelInfo` carries the model `id`, per-million input/output cost,
   and capability flags. `get_model(provider, tier)` resolves one.
3. **Auth strategy** — `AuthStrategy` decides, per module, whether to
   run on your subscription or the API. `AuthMode` is `SUBSCRIPTION`,
   `API`, or `AUTO` (size-based). The strategy is persisted at
   `~/.attune/auth_strategy.json` (`AUTH_STRATEGY_FILE`).

### The three tiers

| Tier | Enum value | Use for |
|------|-----------|---------|
| `CHEAP` | `"cheap"` | summarize, classify, triage, lint, format, simple Q&A |
| `CAPABLE` | `"capable"` | generate code, fix bugs, review security, write tests, refactor |
| `PREMIUM` | `"premium"` | coordinate, synthesize, architectural decisions, final review |

`get_tier_for_task(task_type)` returns the `ModelTier` for a task
string or `TaskType`; `get_tasks_for_tier(tier)` lists the task strings
in a tier.

### Core data structures

| Type | What it represents |
|------|--------------------|
| `ModelInfo` | One model: `id`, `provider`, `tier`, `input_cost_per_million`, `output_cost_per_million`, `max_tokens`, `supports_vision`, `supports_tools`. Convenience properties `cost_per_1k_input` / `cost_per_1k_output` / `model_id` / `name` are read-only. |
| `AuthStrategy` | Auth configuration: `subscription_tier`, `default_mode`, the small/medium LOC thresholds, and `setup_completed`. Note `setup_completed` is a plain field, not a method. |
| `LLMResponse` | A completed call: `content`, `model_id`, `provider`, `tier`, `tokens_input`, `tokens_output`, `cost_estimate`, `latency_ms`. Aliased properties `cost`, `total_tokens`, `success`, `input_tokens`, `output_tokens` are read-only. |
| `ProviderConfig` | Provider selection: `mode` (`ProviderMode.SINGLE`), `primary_provider`, `available_providers`, `cost_optimization`. |

### How auth resolves a mode

`AuthStrategy.get_recommended_mode(module_lines)` resolves by
**subscription tier first, not by size**. If `default_mode` is not
`AUTO`, it returns that. In `AUTO`, the `PRO` and `API_ONLY` tiers
always return `AuthMode.API` (pay-per-token is more economical there)
and module size is never consulted. Only `MAX` / `ENTERPRISE` tiers use
the size thresholds: modules under `small_module_threshold` (500) — and
medium modules under `medium_module_threshold` (2000) when
`prefer_subscription` is set — favor the subscription; larger ones
favor the API for its 1M context window. The zero-config default tier
is `PRO`, so out of the box `AUTO` returns `API` regardless of size.
`estimate_cost(module_lines, mode)` returns the projected cost for a
given mode so you can compare before committing.

## Design & extension

### Design decisions

- **Single provider, tiered models.** `ModelProvider` has one member
  (`ANTHROPIC`) and `ProviderMode.HYBRID` is retained only for
  backward compatibility. The abstraction is kept so adding a provider
  later is a registry change, not an architecture change, but the
  supported surface today is Anthropic-only — `get_model` enforces it.
- **Tasks classify into tiers, not models.** Routing maps a task to a
  `ModelTier` (`TASK_TIER_MAP`), and the tier maps to a concrete model
  separately. This decouples "how hard is this task" from "which model
  is current," so a model swap is a registry edit with no routing
  changes.
- **Auth strategy persists to a file, not env.** `AuthStrategy` saves
  to `~/.attune/auth_strategy.json` so the choice survives across
  sessions and is inspectable. `AUTO` keeps the decision adaptive
  (size-based) rather than hard-coding a mode.
- **Adaptive routing degrades gracefully.** `AdaptiveModelRouter`
  requires `MIN_SAMPLE_SIZE` observations before it overrides the
  static tier choice, so a cold system behaves identically to static
  routing.

### Extension points

- **Add a task type:** add a `TaskType` member and its `.value` to the
  appropriate tier set (`CHEAP_TASKS`, `CAPABLE_TASKS`, or
  `PREMIUM_TASKS`). `TASK_TIER_MAP` is derived from those sets, so
  `get_tier_for_task` and `get_tasks_for_tier` pick it up
  automatically.
- **Add or re-price a model:** edit `MODEL_REGISTRY`; `get_model`,
  `get_all_models`, and `get_pricing_for_model` reflect it with no
  other changes.
- **Plug in a custom executor:** implement the `LLMExecutor` protocol
  (`async run`, `get_model_for_task`, `estimate_cost`). `MockLLMExecutor`
  is the reference implementation.
- **Tune adaptive routing:** pass `max_cost`, `max_latency_ms`, or
  `min_success_rate` to `AdaptiveModelRouter.get_best_model`, or read
  `get_routing_stats` to drive your own selection logic.

<!-- attune-generated: source_hash=52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668 feature=models kind=architecture generated_at=2026-07-14 -->
