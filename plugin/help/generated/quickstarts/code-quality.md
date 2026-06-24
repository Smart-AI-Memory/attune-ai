---
name: code-quality
source: content/features/code-quality.md
tags:
- review
- quality
- bugs
- lint
type: quickstart
---

# Multi-subagent code review across security, quality, performance, and architecture

## Quickstart

Review a directory and print the consolidated report.
`CodeReviewWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed review
    print(result.summary)          # short health summary
    print(result.final_output)     # the full consolidated report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest review.
