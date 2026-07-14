---
type: warning
name: models-warning
feature: models
depth: warning
generated_at: 2026-07-14T15:58:54.871943+00:00
source_hash: 52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668
status: generated
---

# LLM authentication, provider routing, and tier management

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
