---
type: quickstart
name: doc-gen-quickstart
feature: doc-gen
depth: quickstart
generated_at: 2026-06-23T16:17:04.175824+00:00
source_hash: bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384
status: generated
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
