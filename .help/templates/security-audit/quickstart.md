---
type: quickstart
name: security-audit-quickstart
feature: security-audit
depth: quickstart
generated_at: 2026-06-23T12:50:51.607005+00:00
source_hash: e6418a3912ca1198d747373f96c129051dd6130394ad9f787b25fd12acf68e4a
status: generated
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Quickstart

Audit a directory and print the synthesized report.
`SecurityAuditWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import SecurityAuditWorkflow


async def main() -> None:
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed audit
    print(result.summary)          # short posture summary
    print(result.final_output)     # the full synthesized report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for a
longer, extended-thinking audit.
