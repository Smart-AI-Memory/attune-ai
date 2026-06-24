---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: quickstart
---

# Generate new documentation from source code with three specialized subagents

## Quickstart

Generate documentation for a directory and print the result.
`DocumentGenerationWorkflow.execute` is an async coroutine, so
drive it with `asyncio.run` (or `await` it inside an existing event
loop):

```python
import asyncio

from attune.workflows import DocumentGenerationWorkflow


async def main() -> None:
    workflow = DocumentGenerationWorkflow()
    result = await workflow.execute(path="src/attune/config.py")

    print(result.success)          # True on a completed run
    print(result.summary)          # short overview
    print(result.final_output)     # the generated documentation


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="...")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest treatment.
