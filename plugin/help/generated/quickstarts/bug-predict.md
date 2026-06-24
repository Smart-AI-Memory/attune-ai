---
name: bug-predict
source: content/features/bug-predict.md
tags:
- bugs
- prediction
- scanning
- race-condition
type: quickstart
---

# Predict likely bug hotspots with three Agent SDK subagents

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
