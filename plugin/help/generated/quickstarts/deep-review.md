---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: quickstart
---

# Multi-pass code review across security, quality, and test gaps

## Quickstart

Review a directory and print the consolidated report.
`DeepReviewAgentSDKWorkflow.execute` is an async coroutine, so
drive it with `asyncio.run` (or `await` it inside an existing
event loop):

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed review
    print(result.summary)          # short health summary
    print(result.final_output)     # the full consolidated report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest review.
