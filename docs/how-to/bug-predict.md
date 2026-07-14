# Bug Predict

## Quickstart

Scan a directory and print the synthesized report.
`BugPredictionWorkflow.execute` is an async coroutine, so drive
it with `asyncio.run` (or `await` it inside an existing event
loop):

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed scan
    print(result.summary)          # short executive summary
    print(result.final_output)     # the full synthesized report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for a
longer, costlier scan.

## Tasks

### Scan a path from the CLI

**Goal:** run a one-off prediction over a directory without
writing any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run bug-predict --path src/

# Deeper scan, JSON output for a CI step:
attune workflow run bug-predict --path src/ --depth deep --json

# Cost-saving pass (unpinned subagents run on Haiku):
attune workflow run bug-predict --path src/ --cheap
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output; `--cheap` forces every subagent
without an explicit model onto Haiku for that run. Use
`attune workflow info bug-predict` to confirm the workflow is
registered, and `attune workflow list` to see it alongside the
other workflows.

### Call the prediction from Python

**Goal:** drive bug-predict from a hook or custom tool and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path="src/api/", depth="quick")

    if not result.success:
        print("scan failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
scan returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns` actually used.

### Steer the scan with a prompt suffix

**Goal:** narrow or focus the analysis without replacing the
built-in orchestrator behavior.

**Steps:**

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow(
        system_prompt_suffix=(
            "Focus on authentication code. "
            "Skip LOW severity findings."
        ),
    )
    result = await workflow.execute(path="src/auth/")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** `system_prompt_suffix` is a keyword-only constructor
argument appended to the orchestrator's system prompt at call
time. The three subagents still run their normal analysis; the
suffix only steers the orchestrator. The empty-string default
leaves behavior unchanged (this is the hook discovery-sweep's
`BugPredictSource` uses to augment the prompt per instance).

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

<!-- attune-generated: source_hash=6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208 feature=bug-predict kind=how-to generated_at=2026-07-14 -->
