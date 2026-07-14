---
type: task
name: code-quality-task
feature: code-quality
depth: task
generated_at: 2026-07-14T15:58:49.270997+00:00
source_hash: 1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679
status: generated
---

# Multi-subagent code review across security, quality, performance, and architecture

## Tasks

### Review a path from the CLI

**Goal:** run a one-off review over a directory without writing any
Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run code-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run code-review --path src/ --depth deep --json
```

**Verify:** the slug is `code-review` (not `code-quality`).
`--path` / `-p` defaults to the current directory; `--depth`
accepts `quick`, `standard`, or `deep`; `--json` / `-j` emits
machine-readable output. Use `attune workflow info code-review` to
confirm registration and `attune workflow list` to see it alongside
the other workflows.

### Call the review from Python

**Goal:** drive code-quality from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
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
review returns `success=True` with the report in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope a review to a smaller area

**Goal:** keep a run fast and cheap by narrowing what it reads.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()

    # A single subsystem, quick pass:
    result = await workflow.execute(path="src/auth/", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** code-quality has no `focus` parameter, so the only
levers are `path` (point it at a narrower directory or file) and
`depth` (`quick` trims the agent-turn budget to 10). All four passes
still run over whatever `path` covers.
