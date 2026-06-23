---
type: task
name: rag-grounding-task
feature: rag-grounding
depth: task
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Tasks

### Generate a grounded answer from Python

**Goal:** answer a coding question grounded in attune docs, with
citations.

**Steps:**

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="How do I customize release gates?", k=5)

    if not result.success:
        print("generation failed:", result.error)
        return

    print(result.final_output)               # answer + ## Sources
    print(result.metadata["citation"])       # structured provenance


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. `k` controls how
many passages are retrieved. The output ends with a `## Sources` block;
`metadata["citation"]["hits"]` lists each cited template with its
`template_path`, `category`, and `score`.

### Run it from the CLI

**Goal:** get a grounded answer without writing Python.

**Steps:**

```bash
# query is passed as JSON input; the workflow slug is rag-code-gen:
attune workflow run rag-code-gen --input '{"query": "how do I run a security audit?"}'

# deeper run, JSON output:
attune workflow run rag-code-gen --input '{"query": "...", "k": 5}' --depth deep --json
```

**Verify:** the slug is `rag-code-gen` (not `rag-grounding`, which is
the feature/help name). `--input` / `-i` takes JSON carrying `query`
(and optional `k`); `--depth` accepts `quick` / `standard` / `deep`;
`--json` / `-j` emits machine-readable output.

### Tune retrieval breadth and cost

**Goal:** trade grounding breadth against speed and cost.

**Steps:**

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="explain the memory tiers", k=2, depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** lower `k` retrieves fewer passages (faster, narrower
grounding); `quick` uses the smallest turn budget (6) and lowest cap
($2). `metadata["retrieval_ms"]` reports retrieval time.
