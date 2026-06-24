---
name: rag-grounding
source: content/features/rag-grounding.md
tags:
- rag
- retrieval
- grounding
- faithfulness
- citation
type: quickstart
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
