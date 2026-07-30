---
type: quickstart
name: fix-test-quickstart
feature: fix-test
depth: quickstart
generated_at: 2026-06-22T11:30:53.046085+00:00
source_hash: 2a68f682c715ddba2510a8395022ba9b502452e2fce1c7a1d13419ce2a2f0f1b
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Fastest path: /fix-test in Claude Code

For an interactive fix, run `/fix-test <test file or pattern>` in a
Claude Code session — it scopes the target, classifies the root
cause, applies a fix, and re-runs (up to 3 attempts) before
reporting. The full walkthrough, including wiring a tests-on-edit
hook so failures are caught and fixed the moment an edit creates
them, is the tutorial at `docs/tutorials/fix-test.md`.

## Quickstart (Python API)

Generate a maintenance plan for the whole project.
`TestMaintenanceWorkflow.run` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")
    result = await workflow.run({"mode": "analyze"})
    print(result["status"])               # "plan_generated"
    print(result["message"])              # "Generated plan with N items"
    for item in result["plan"]["items"]:
        print(item["priority"], item["action"], item["file_path"])


asyncio.run(main())
```

`run` returns a plain dict (the plan is `result["plan"]`, already
serialized via `TestMaintenancePlan.to_dict`). The `"analyze"` mode
only *plans* — it never writes tests. Use `"auto"` to execute the
items flagged `auto_executable`, or `"report"` for a health summary.
