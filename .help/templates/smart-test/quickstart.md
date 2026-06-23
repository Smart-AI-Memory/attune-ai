---
type: quickstart
name: smart-test-quickstart
feature: smart-test
depth: quickstart
generated_at: 2026-06-23T15:57:46.208360+00:00
source_hash: d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe
status: generated
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

## Quickstart

Audit a directory for coverage gaps and print the report.
`TestAuditWorkflow.execute` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import TestAuditWorkflow


async def main() -> None:
    workflow = TestAuditWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed audit
    print(result.summary)          # short coverage summary
    print(result.final_output)     # the full gap report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest audit.
