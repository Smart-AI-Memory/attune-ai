---
type: quickstart
name: release-notes-quickstart
feature: release-notes
depth: quickstart
generated_at: 2026-06-23T21:24:13.287162+00:00
source_hash: 3bee45ea7e9bedc48f6fdc7744f2c05ff0fd177419dba9606233f53b10818ab6
status: generated
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

## Quickstart

Draft release notes for a project and print the result.
`ReleasePreparationWorkflow.execute` is an async coroutine, so drive
it with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".")

    print(result.success)          # True on a completed run
    print(result.summary)          # readiness score + go/no-go
    print(result.final_output)     # the synthesized report + changelog


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path=".")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the fullest
treatment.
