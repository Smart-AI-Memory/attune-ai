---
name: refactor-plan
source: content/features/refactor-plan.md
tags:
- refactor
- tech-debt
- complexity
type: task
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Tasks

### Generate a roadmap from the CLI

**Goal:** produce a prioritized refactoring plan for a directory
without writing any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run refactor-plan --path src/

# Deep analysis, JSON output for a report:
attune workflow run refactor-plan --path src/ --depth deep --json
```

**Verify:** the slug is `refactor-plan`. `--path` / `-p` defaults
to the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use
`attune workflow info refactor-plan` to confirm registration.

### Call the planner from Python

**Goal:** drive refactor-plan from a hook or scheduled report and
act on the result.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/legacy/", depth="deep")

    if not result.success:
        print("analysis failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the roadmap in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope the analysis to a smaller area

**Goal:** keep a run fast and focused on the module you care about.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/attune/config.py", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** refactor-plan has no `focus` parameter, so the levers
are `path` (point it at a narrower directory or file) and `depth`
(`quick` trims the agent-turn budget to 10). All three passes run
over whatever `path` covers.
