---
type: quickstart
name: code-quality-quickstart
feature: code-quality
depth: quickstart
generated_at: 2026-06-23T15:45:20.604236+00:00
source_hash: 3f9592fd884ddc994048dbdc80fa264339717c64b37d33385ef2e36088c41472
status: generated
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
