# Bug Predict

## Reference

Bug-predict's public surface is the `BugPredictionWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `BugPredictionWorkflow` — `attune.workflows.bug_predict`

| Symbol | Purpose |
|--------|---------|
| `BugPredictionWorkflow(*, system_prompt_suffix="", **kwargs)` | Construct the workflow. `system_prompt_suffix` (keyword-only) is appended to the orchestrator's system prompt; the empty default preserves stock behavior. Other kwargs pass to `BaseWorkflow`. |
| `BugPredictionWorkflow.execute(**kwargs)` | **Async.** Run the prediction. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`); other kwargs are ignored. Returns a `WorkflowResult`. |
| `BugPredictionWorkflow.name` | The registered slug, `"bug-predict"`. |
| `BugPredictionWorkflow.stages` | `["agent-predict"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast first pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | A thorough scan of a large or high-risk area. |

### `WorkflowResult` fields read after a scan

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the scan completed. |
| `final_output` | `Any` | The synthesized report — a serialized `WorkflowReport` when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short executive summary of the run. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/bug-predict` in a Claude Code conversation. |
| CLI | `attune workflow run bug-predict --path <p> [--depth quick\|standard\|deep] [--json] [--cheap]`. |
| MCP tool | `bug_predict` — one required `path` argument; runs at standard depth (the handler does not pass `depth`). |
| Python | `await BugPredictionWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208 feature=bug-predict kind=reference generated_at=2026-07-14 -->
