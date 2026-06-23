# Deep Review

## Reference

Deep-review's public surface is the `DeepReviewAgentSDKWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `DeepReviewAgentSDKWorkflow` — `attune.workflows.deep_review`

| Symbol | Purpose |
|--------|---------|
| `DeepReviewAgentSDKWorkflow()` | Construct the workflow. Takes no special constructor arguments (no `system_prompt_suffix`). |
| `DeepReviewAgentSDKWorkflow.execute(**kwargs)` | **Async.** Run the review. Honors `path` (str, required), `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`), and `focus` (list of `"security"` / `"quality"` / `"test-gaps"`, default all three). Returns a `WorkflowResult`. |
| `DeepReviewAgentSDKWorkflow.name` | The registered slug, `"deep-review"`. |
| `DeepReviewAgentSDKWorkflow.stages` | `["deep-review"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 15 | A fast pass on a small path. |
| `standard` | 30 | The default — balanced coverage and cost. |
| `deep` | 50 | The fullest review of a large or critical area. |

### The three passes

| `focus` value | Subagent | Domain |
|---------------|----------|--------|
| `security` | `security-reviewer` | Injection, secrets, path traversal, auth, OWASP Top 10. |
| `quality` | `quality-reviewer` | Complexity, broad excepts, dead code, naming, duplication, type hints, docstrings, long functions. |
| `test-gaps` | `test-gap-reviewer` | Untested paths, missing edge cases, weak assertions, mocks hiding bugs. |

### `WorkflowResult` fields read after a review

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the review completed. |
| `final_output` | `Any` | The consolidated report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short health summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, `focus`, and `workflow`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/deep-review` in a Claude Code conversation. |
| CLI | `attune workflow run deep-review --path <p> [--depth quick\|standard\|deep] [--json] [--input '{"focus": [...]}']`. |
| MCP tool | `deep_review` — one required `path` argument; runs all three passes at standard depth (the handler does not pass `depth` or `focus`). |
| Python | `await DeepReviewAgentSDKWorkflow().execute(path=<p>, depth=<d>, focus=[...])`. |

<!-- attune-generated: source_hash=5e2ccde04cab83b41196f2c5f05ef11b8e7be00e39bb8040b02fb2a225aef083 feature=deep-review kind=reference generated_at=2026-06-23 -->
