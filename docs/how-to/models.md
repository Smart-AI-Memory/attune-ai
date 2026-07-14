# Models

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

<!-- attune-generated: source_hash=52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668 feature=models kind=how-to generated_at=2026-07-14 -->
