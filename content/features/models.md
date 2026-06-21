---
feature: models
summary: LLM authentication, provider routing, and tier management
tags: [models, auth, llm]
source_globs: [src/attune/models/**]
cli: { command: auth }
nav:
  help: models
  mkdocs:
    how-to: how-to/models
    architecture: architecture/models
    reference: reference/models
---

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

## Quickstart

Inspect the active routing and pricing in a single Python call:

```python
from attune.models import get_tier_for_task, get_model, get_pricing_for_model

tier = get_tier_for_task("generate_code")     # ModelTier.CAPABLE
model = get_model("anthropic", tier.value)    # ModelInfo | None
print(model.id, model.cost_per_1k_input)      # cost_per_1k_input is a property

pricing = get_pricing_for_model(model.id)     # {"input": ..., "output": ...} per million
print(pricing)
```

`cost_per_1k_input` and `cost_per_1k_output` are **properties** — read
them, don't call them. `get_model` returns `None` if no model is
registered for that provider/tier, so guard the result before using it.

From the shell, the same information and your auth posture:

```bash
attune auth status          # current auth strategy
attune provider show        # current provider
```

## Tasks

### See which model a task will use

**Goal:** resolve the tier and concrete model for a task type without
running anything.

**Steps:**

```python
from attune.models import (
    get_tier_for_task,
    get_tasks_for_tier,
    get_model,
    is_known_task,
)

task = "review_security"
print(is_known_task(task))            # True
tier = get_tier_for_task(task)        # ModelTier.CAPABLE
model = get_model("anthropic", tier.value)
print(f"{task} -> {tier.value} -> {model.id if model else 'unregistered'}")

# What else runs at this tier?
print(get_tasks_for_tier(tier))       # list[str] of task names
```

**Verify:** `get_tier_for_task` returns a `ModelTier`. An unknown task
string does not raise — it defaults to `ModelTier.CAPABLE`; use
`is_known_task` first if you need to distinguish.

### Configure your authentication strategy

**Goal:** choose subscription vs API and persist the choice.

**Steps:** run the interactive CLI, then confirm it:

```bash
attune auth setup            # interactive: pick subscription tier + default mode
attune auth status           # human-readable summary
attune auth status --json    # machine-readable, for scripts/CI
```

Or programmatically:

```python
from attune.models import get_auth_strategy, AuthMode

strategy = get_auth_strategy()                 # zero-config default if unset
mode = strategy.get_recommended_mode(1800)     # API on a PRO account; size-based only on MAX/ENTERPRISE
estimate = strategy.estimate_cost(1800, mode)  # mode, monetary_cost, quota_cost, tokens_used, fits_in_context
print(mode.value, estimate)
strategy.save()                                # persists to AUTH_STRATEGY_FILE
```

**Verify:** `attune auth status --json` reports the active mode and
tier. `get_recommended_mode` returns an `AuthMode` member whose
`.value` is `"subscription"` or `"api"` — never `"auto"` (`AUTO` is the
input that triggers resolution). Note `setup_completed` defaults to
`true`, so status reports it `true` even before you run setup.

### Get a per-file auth recommendation

**Goal:** ask which mode a specific file should use, given its size.

**Steps:**

```bash
attune auth recommend src/attune/models/registry.py
```

The command counts the file's lines of code and prints the recommended
mode plus a cost estimate. The Python equivalent pairs
`count_lines_of_code` with `get_recommended_mode`:

```python
from attune.models import count_lines_of_code, get_auth_strategy

loc = count_lines_of_code("src/attune/models/registry.py")
mode = get_auth_strategy().get_recommended_mode(loc)
print(loc, mode.value)
```

**Verify:** the CLI exits `0` and names a mode. `count_lines_of_code`
counts non-blank, non-comment lines, so its result is smaller than a
raw `wc -l`.

### Change the provider configuration

**Goal:** inspect or set the active provider.

**Steps:**

```bash
attune provider show         # print current provider + mode
attune provider set          # interactive provider selection
```

Programmatically:

```python
from attune.models import get_provider_config, set_provider_config, ProviderConfig

cfg = get_provider_config()                    # lazy-loaded global
print(cfg.mode, cfg.primary_provider)          # ProviderMode.SINGLE anthropic

cfg = ProviderConfig.auto_detect()             # detect ANTHROPIC_API_KEY
set_provider_config(cfg)                        # install as the global
```

**Verify:** `attune provider show` reflects the change.
`ProviderConfig.auto_detect()` returns a config whose
`available_providers` includes `"anthropic"` when `ANTHROPIC_API_KEY`
is set.

### Reset auth configuration

**Goal:** clear a misconfigured auth strategy.

**Steps:**

```bash
attune auth reset --confirm
```

**Verify:** the configuration file is removed; a subsequent
`attune auth status` shows the zero-config default and prompts you to
run `attune auth setup`.

## Reference

The subsystem's public API lives under `attune.models`. The two CLI
namespaces are `attune auth` (authentication) and `attune provider`
(provider selection).

### CLI — `attune auth`

| Command | Purpose |
|---------|---------|
| `attune auth setup` | Configure the auth strategy interactively. |
| `attune auth status` | Show the current strategy. `--json` emits machine-readable output. |
| `attune auth recommend <file_path>` | Print the recommended mode and cost estimate for one file. |
| `attune auth reset` | Clear the saved strategy. Requires `--confirm`. |

### CLI — `attune provider`

| Command | Purpose |
|---------|---------|
| `attune provider show` | Print the current provider and mode. |
| `attune provider set` | Select a provider interactively. |

### Registry and tiers

| Symbol | Purpose |
|--------|---------|
| `MODEL_REGISTRY` | `dict[str, dict[str, ModelInfo]]` keyed by provider then tier. |
| `ModelTier` | Enum: `CHEAP`, `CAPABLE`, `PREMIUM` (values `"cheap"`/`"capable"`/`"premium"`). |
| `ModelProvider` | Enum: `ANTHROPIC` (`"anthropic"`). |
| `get_model(provider, tier)` | Resolve one `ModelInfo` (or `None`). Raises `ValueError` if provider is not `"anthropic"`. |
| `get_all_models()` | Return the full registry. |
| `get_pricing_for_model(model_id)` | `{"input": float, "output": float}` per million, or `None`. |

### Task routing

| Symbol | Purpose |
|--------|---------|
| `TaskType` | Enum of known task types (e.g. `GENERATE_CODE`, `SUMMARIZE`). |
| `TASK_TIER_MAP` | `dict[str, ModelTier]` mapping task value → tier. |
| `get_tier_for_task(task_type)` | `ModelTier` for a task string or `TaskType` (defaults to `CAPABLE`). |
| `get_tasks_for_tier(tier)` | `list[str]` of task names in a tier. Raises `ValueError` on an unknown tier. |
| `is_known_task(task_type)` | `True` if the task is defined. |
| `normalize_task_type(task_type)` | Lowercase/underscore-normalize a task string. |

### Auth and provider

| Symbol | Purpose |
|--------|---------|
| `AuthMode` | Enum: `SUBSCRIPTION`, `API`, `AUTO`. |
| `AuthStrategy` | Auth configuration dataclass; `setup_completed` is a field. |
| `AuthStrategy.get_recommended_mode(module_lines)` | Recommended `AuthMode`. Resolves by tier first (`PRO`/`API_ONLY` → `API`); only `MAX`/`ENTERPRISE` use `module_lines` against the thresholds. Returns `SUBSCRIPTION` or `API`, never `AUTO`. |
| `AuthStrategy.estimate_cost(module_lines, mode=None)` | `dict` with `mode`, `monetary_cost`, `quota_cost`, `tokens_used`, `fits_in_context`. |
| `get_auth_strategy()` | The global `AuthStrategy` (zero-config default if unset). |
| `count_lines_of_code(file_path)` | Non-blank, non-comment line count for a Python file. |
| `ProviderConfig` | Provider config dataclass; `mode` is a `ProviderMode`. |
| `ProviderMode` | Enum: `SINGLE`, `HYBRID` (deprecated). |
| `get_provider_config()` / `set_provider_config(cfg)` / `reset_provider_config()` | Read, replace, and reset the global provider config. |

### Execution and routing

| Symbol | Purpose |
|--------|---------|
| `LLMResponse` | Completed-call result. `cost`, `total_tokens`, `success`, `input_tokens`, `output_tokens` are read-only properties over the underlying fields. |
| `ExecutionContext` | Per-call hints: `task_type`, `provider_hint`, `tier_hint`, `timeout_seconds`, `metadata`. |
| `LLMExecutor` | Executor protocol. Its `run(task_type, prompt, ...)` is **async** — `await` it. |
| `MockLLMExecutor` | A deterministic executor for tests; records calls in `call_history`. |
| `AdaptiveModelRouter` | Picks a model from historical telemetry. `get_best_model(workflow, stage, ...)` returns a model id; `recommend_tier_upgrade(workflow, stage)` returns `(bool, reason)`. |

## Comparison

Two layers select a model, and they differ in whether the choice is
static (tier-mapped) or learned (telemetry-driven).

| Capability | Static routing (`get_tier_for_task` + `get_model`) | Adaptive routing (`AdaptiveModelRouter`) |
|---|---|---|
| **Input** | Task type string | Workflow + stage history |
| **Decision basis** | `TASK_TIER_MAP` (fixed) | Observed success rate, latency, cost |
| **Determinism** | Fully deterministic | Depends on telemetry sample size |
| **Cold start** | Works immediately | Needs `MIN_SAMPLE_SIZE` (10) calls first |
| **Cost control** | Tier choice only | `max_cost` / `max_latency_ms` / `min_success_rate` filters |
| **Typical caller** | Any workflow, default path | Long-running workflows that accumulate stats |

**Use static routing** by default — it is predictable and needs no
history. **Use adaptive routing** when a workflow runs often enough to
accumulate telemetry and you want the router to escalate or downgrade
tiers based on real outcomes. Adaptive routing falls back to static
behavior until it has enough samples.

For auth, the analogous fork is `AuthMode`: `SUBSCRIPTION` and `API`
are explicit; `AUTO` defers to `get_recommended_mode`, which resolves
by subscription tier (and, only for `MAX`/`ENTERPRISE`, module size).
Prefer `AUTO` unless you have a reason to pin one mode.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `ValueError` from `get_model` | Provider other than `"anthropic"` passed | Pass `"anthropic"`; this provider set is single today | high |
| `get_model(...)` returns `None` | No model registered for that provider/tier | Check the tier value (`ModelTier.CHEAP.value`, not the enum) and guard the result | high |
| `ValueError` from `get_tasks_for_tier` | Unknown tier argument | Pass a real `ModelTier`, not a raw string | medium |
| A task routes to `CAPABLE` unexpectedly | The task string is unknown, so it defaulted | Call `is_known_task` first; add the task to the tier map if it should be classified | medium |
| `AUTO` returns `API` on a PRO account regardless of module size | `get_recommended_mode` resolves by tier first; `PRO`/`API_ONLY` always return `API` | Expected — only `MAX`/`ENTERPRISE` tiers use size-based selection | medium |
| Auth always picks the mode you set, ignoring `AUTO` logic | `default_mode` is `SUBSCRIPTION` or `API`, not `AUTO` | Set `default_mode = AuthMode.AUTO` so it defers to `get_recommended_mode` | medium |
| `await` error calling an executor's `run` | `LLMExecutor.run` is async and was called without `await` | `await executor.run(...)` or drive it with `asyncio.run` | medium |
| `AdaptiveModelRouter` returns the same model regardless of cost | Fewer than `MIN_SAMPLE_SIZE` calls recorded | Accumulate telemetry; until then it falls back to static defaults | low |

### Risk areas

- **Tier value vs enum.** Registry lookups take the tier **value**
  (`tier.value`), while routing functions accept either a `ModelTier`
  or its string. Mixing the two silently returns `None` from
  `get_model`. Pass `tier.value` to `get_model`.
- **Unknown tasks default silently.** `get_tier_for_task` never raises;
  an unrecognized task quietly becomes `CAPABLE`. Validate with
  `is_known_task` when the task source is untrusted.
- **Cost fields are per-million on `ModelInfo`, per-1k on the
  properties.** `input_cost_per_million` is the stored field;
  `cost_per_1k_input` is the derived property. Don't mix the units when
  computing an estimate.
- **`get_provider_config` is a lazy global.** It loads once and caches;
  call `reset_provider_config()` after writing a new config file if you
  need the change to take effect in a long-lived process.

### Diagnosis order

1. Print the resolved tier: `get_tier_for_task(task)` — confirms the
   classification before any model lookup.
2. Print the model: `get_model("anthropic", tier.value)` — `None` means
   a registry gap or a tier passed as an enum instead of `.value`.
3. Inspect auth: `attune auth status --json` — confirms
   `setup_completed` and the active mode.
4. Inspect provider: `attune provider show` — confirms the provider and
   mode the lookups will use.
5. For routing surprises, read `AdaptiveModelRouter.get_routing_stats(
   workflow, stage)` to see sample size and per-model performance.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3 and this spec's
> [decisions.md](../../docs/specs/help-docs-single-source/decisions.md)
> D6/D7). This section is **not** projected verbatim; it contributes
> the feature's seed questions to the Generator.

- **Q:** How does Attune decide which model to use?
  **A:** Each task type maps to a tier (`CHEAP`/`CAPABLE`/`PREMIUM`)
  via `TASK_TIER_MAP`, and each tier maps to a model in
  `MODEL_REGISTRY`. `get_tier_for_task` then `get_model` resolves it;
  unknown tasks default to `CAPABLE`.
- **Q:** Subscription or API — which should I use?
  **A:** Use `AuthMode.AUTO` and let `get_recommended_mode` decide, or
  run `attune auth setup` to pin a default. On `PRO`/`API_ONLY`
  accounts `AUTO` always picks the API; only `MAX`/`ENTERPRISE`
  accounts get size-based selection (subscription for small/medium
  modules, API for large).
- **Q:** How do I see the cost of a model?
  **A:** `get_pricing_for_model(model_id)` returns per-million input and
  output costs; `ModelInfo.cost_per_1k_input` / `cost_per_1k_output`
  give the per-1k equivalents (they are properties).
- **Q:** Why did my task pick a more expensive model than I expected?
  **A:** Either the task classifies into a higher tier, or an
  `AdaptiveModelRouter` escalated based on telemetry. Check
  `get_tier_for_task(task)` and, if adaptive, `get_routing_stats`.
- **Q:** What providers are supported?
  **A:** Anthropic. `ModelProvider` has a single member today and
  `get_model` raises `ValueError` for anything else.

## Notes & tips

- **Depend only on the public API.** `attune.models` re-exports the
  registry (`MODEL_REGISTRY`, `ModelInfo`, `ModelTier`, `get_model`,
  `get_all_models`, `get_pricing_for_model`), task routing
  (`TaskType`, `get_tier_for_task`, `get_tasks_for_tier`,
  `is_known_task`), auth (`AuthStrategy`, `AuthMode`,
  `get_auth_strategy`), provider config (`ProviderConfig`,
  `ProviderMode`, `get_provider_config`), and execution (`LLMExecutor`,
  `LLMResponse`, `ExecutionContext`, `MockLLMExecutor`,
  `AdaptiveModelRouter`). Treat anything not exported as private.
- **Pass `tier.value` to the registry.** `get_model` and the registry
  key on the string value; the routing functions accept the enum. When
  in doubt, `.value`.
- **`get_recommended_mode` is pure.** It reads the strategy's
  `subscription_tier`, `default_mode`, thresholds, and the LOC argument
  — no I/O — so it is safe to call in tight loops or tests.
- **Use `MockLLMExecutor` in tests.** It satisfies the `LLMExecutor`
  protocol, returns a deterministic `LLMResponse`, and records calls in
  `call_history` for assertions — no network, no spend.

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
