---
type: quickstart
name: refactor-plan-quickstart
feature: refactor-plan
depth: quickstart
generated_at: 2026-06-23T16:06:40.108874+00:00
source_hash: 198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb
status: generated
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
