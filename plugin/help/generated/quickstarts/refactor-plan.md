---
name: refactor-plan
source: content/features/refactor-plan.md
tags:
- refactor
- tech-debt
- complexity
type: quickstart
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Quickstart

Analyze a directory and print the refactoring roadmap.
`RefactorPlanWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed analysis
    print(result.summary)          # short tech-debt summary
    print(result.final_output)     # the full roadmap


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest roadmap.
