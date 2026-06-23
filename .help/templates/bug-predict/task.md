---
type: task
name: bug-predict-task
feature: bug-predict
depth: task
generated_at: 2026-06-23T12:37:44.972124+00:00
source_hash: 3c6441a981e2df351b5043ad522cb27f0fed3c7907db1157a7f65632cc74504d
status: generated
---

# Predict likely bug hotspots with three Agent SDK subagents

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
