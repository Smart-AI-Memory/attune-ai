# Code Quality

## Reference

Code-quality's public surface is the `CodeReviewWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `CodeReviewWorkflow` — `attune.workflows.code_review`

| Symbol | Purpose |
|--------|---------|
| `CodeReviewWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `CodeReviewWorkflow.execute(**kwargs)` | **Async.** Run the review. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `CodeReviewWorkflow.name` | The registered slug, `"code-review"`. |
| `CodeReviewWorkflow.stages` | `["agent-review"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest review of a large or critical area. |

### The four passes

| Subagent | Domain |
|----------|--------|
| `security-reviewer` | eval/exec, injection, path traversal, secrets, auth. |
| `quality-reviewer` | Complexity, error handling, naming, duplication, test-coverage gaps. |
| `perf-reviewer` | N+1, unnecessary copies, blocking I/O in async, missing caching. |
| `architect-reviewer` | Coupling, SOLID, circular deps, API design, abstraction mismatches. |

### `WorkflowResult` fields read after a review

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the review completed. |
| `final_output` | `Any` | The consolidated report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short health summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, and `subagent_transcripts`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/code-quality` in a Claude Code conversation — routes by depth to `code_review` (quick), `code_review` + `bug_predict` (thorough), or `deep_review` (deep). |
| CLI | `attune workflow run code-review --path <p> [--depth quick\|standard\|deep] [--json]`. |
| MCP tool | `code_review` — one required `path` argument; runs at standard depth (the handler does not pass `depth`) and validates the path against the workspace root. |
| Python | `await CodeReviewWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679 feature=code-quality kind=reference generated_at=2026-07-14 -->
