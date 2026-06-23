# Deep Review

## Quickstart

Review a directory and print the consolidated report.
`DeepReviewAgentSDKWorkflow.execute` is an async coroutine, so
drive it with `asyncio.run` (or `await` it inside an existing
event loop):

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed review
    print(result.summary)          # short health summary
    print(result.final_output)     # the full consolidated report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest review.

## Tasks

### Review a path from the CLI

**Goal:** run a one-off review over a directory without writing
any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run deep-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run deep-review --path src/ --depth deep --json

# Narrow to the security pass via JSON input:
attune workflow run deep-review --path src/ --input '{"focus": ["security"]}'
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output. There is no dedicated `--focus`
flag — pass `focus` through `--input` as JSON. Use
`attune workflow info deep-review` to confirm registration and
`attune workflow list` to see it alongside the other workflows.

### Call the review from Python

**Goal:** drive deep-review from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
    result = await workflow.execute(path="src/api/", depth="deep")

    if not result.success:
        print("review failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
review returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, `max_turns`,
and active `focus`.

### Run only the passes you need

**Goal:** scope the review to one or two domains instead of all
three.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()

    # Security pass only:
    sec = await workflow.execute(path="src/auth/", focus=["security"])
    print(sec.final_output)

    # Security + quality, skip test gaps:
    both = await workflow.execute(
        path="src/auth/", focus=["security", "quality"]
    )
    print(both.final_output)


asyncio.run(main())
```

**Verify:** `focus` accepts any subset of `"security"`,
`"quality"`, `"test-gaps"`. Only the named passes run, and
`metadata["focus"]` reflects the active set. An all-invalid
`focus` returns `success=False` with an "Invalid focus values"
error naming the valid options.

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

<!-- attune-generated: source_hash=5e2ccde04cab83b41196f2c5f05ef11b8e7be00e39bb8040b02fb2a225aef083 feature=deep-review kind=how-to generated_at=2026-06-23 -->
