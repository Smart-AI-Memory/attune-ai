---
type: quickstart
name: deep-review-quickstart
feature: deep-review
depth: quickstart
generated_at: 2026-06-23T15:11:33.648986+00:00
source_hash: 5e2ccde04cab83b41196f2c5f05ef11b8e7be00e39bb8040b02fb2a225aef083
status: generated
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
