---
type: quickstart
name: fix-test-quickstart
feature: fix-test
depth: quickstart
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Quickstart

**Fastest path — `/fix-test` in Claude Code.** For an interactive
fix, run `/fix-test <test file or pattern>` in a Claude Code
session — it scopes the target, classifies the root cause, applies
a fix, and re-runs (up to 3 attempts) before reporting. The full
walkthrough, including wiring a tests-on-edit hook so failures are
caught and fixed the moment an edit creates them, is the tutorial
at `docs/tutorials/fix-test.md`.

For the Python API, generate a maintenance plan for the whole project.
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
