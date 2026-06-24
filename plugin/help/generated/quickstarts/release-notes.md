---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: quickstart
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
