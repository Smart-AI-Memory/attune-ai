---
type: faq
name: rag-grounding-faq
feature: rag-grounding
depth: faq
status: manual
---

# RAG Grounding FAQ

## What is RAG grounding?

It retrieves attune documentation and generates an answer that cites
real APIs, workflow names, and CLI commands — never invented ones —
ending with a markdown `## Sources` block. The class is
`RagCodeGenWorkflow`: it retrieves grounding passages first (via
`attune_rag.RagPipeline`), then a single Claude Agent SDK call
generates against them.

## When should I use it?

Use it when generated code must stay faithful to the attune ecosystem
— when a hallucinated API name or invented workflow reference would be
a problem. For general-purpose generation with no attune grounding, it
adds overhead you may not need.

## Why is the CLI slug `rag-code-gen` but the feature `rag-grounding`?

Both name the same `RagCodeGenWorkflow`. `rag-code-gen` is the
registered workflow slug (used by the CLI and the `/rag-code-gen`
skill); `rag-grounding` is the feature / help topic.

## How do I run it?

- **Python:** `await RagCodeGenWorkflow().execute(query="...")`
  (import from `attune.workflows`).
- **CLI:** `attune workflow run rag-code-gen --input '{"query": "..."}'`.
- **Conversation:** the `/rag-code-gen` skill.

There is no dedicated MCP tool for this workflow.

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="how do I run a security audit?")
    print(result.final_output)   # answer + a ## Sources block


asyncio.run(main())
```

## Are the calls async?

Yes — `execute` is a coroutine. `await` it or drive it with
`asyncio.run`. Calling it without awaiting is the most common mistake.

## Do I need attune-rag installed?

Yes — `attune-rag` is a core dependency (the legacy `[rag]` extra is an
empty placeholder). Without it the first `execute` raises a
`RuntimeError` pointing at `pip install attune-rag`.

## How does citation enforcement work?

The system prompt instructs the model to cite only what the retrieved
context attests and never to invent attune features. Retrieved content
arrives inside `<passage>...</passage>` tags and is treated strictly as
documentation — even a literal `</passage>` escape is read as content,
not a command.

## How do I control how much context is retrieved?

Set `k` (number of passages, default 3) and `depth`
(`quick` / `standard` / `deep` — sets the turn budget and cost cap).

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
