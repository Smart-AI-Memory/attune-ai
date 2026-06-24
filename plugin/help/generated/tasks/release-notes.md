---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: task
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

## Tasks

### Draft release notes from the CLI

**Goal:** draft a changelog and get a go/no-go recommendation without
writing any Python.

**Steps:**

```bash
# Default depth (standard) at the project root:
attune workflow run release-notes --path .

# Deep advisory, JSON output:
attune workflow run release-notes --path . --depth deep --json
```

**Verify:** the slug is `release-notes`. `--path` / `-p` defaults to
the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use `attune
workflow info release-notes` to confirm registration. The report
includes a readiness score, the drafted changelog, and prioritized
next steps — this is advice, not a gate.

### Draft release notes from Python

**Goal:** wire the advisory into a release hook or pipeline and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="deep")

    if not result.success:
        print("advisory failed:", result.error)
        return

    print(result.final_output)     # synthesized report + changelog
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the report in `final_output`; a failure
returns `success=False` with a populated `error`. `metadata` echoes
the `path`, `depth`, and `max_turns`.

### Keep the advisory cheap

**Goal:** run the advisory at the lowest cost.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="quick")
    print(result.summary)


asyncio.run(main())
```

**Verify:** `quick` uses the smallest agent-turn budget (10) and the
lowest cap ($2). To let a deep pre-release run finish without a cap,
export `ATTUNE_MAX_BUDGET_USD=0`. Subscription users pay no
per-request cost regardless.
