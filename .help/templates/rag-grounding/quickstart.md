---
type: quickstart
name: rag-grounding-quickstart
feature: rag-grounding
depth: quickstart
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Quickstart

Ask a grounded question and print the answer with its sources.
`execute` is a coroutine, so drive it with `asyncio.run`:

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="How do I run a security audit?")

    print(result.success)        # True on a completed run
    print(result.final_output)   # generated answer + a ## Sources block


asyncio.run(main())
```

`k` defaults to 3 and `depth` to `"standard"`, so
`execute(query=...)` is equivalent.
