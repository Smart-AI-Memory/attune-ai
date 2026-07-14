# Models

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

<!-- attune-generated: source_hash=52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668 feature=models kind=reference generated_at=2026-07-14 -->
