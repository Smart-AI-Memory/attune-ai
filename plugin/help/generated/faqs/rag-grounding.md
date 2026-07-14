---
name: rag-grounding
source: content/features/rag-grounding.md
tags:
- rag
- retrieval
- grounding
- faithfulness
- citation
type: faq
---

# Rag Grounding FAQ

## What does rag-grounding do?

It retrieves attune documentation and generates an answer that
cites real APIs/workflows/CLI commands — never invented ones —
ending with a `## Sources` block.

## Why is the CLI slug `rag-code-gen` but the feature `rag-grounding`?

Both name the same `RagCodeGenWorkflow`. `rag-code-gen` is the
registered workflow slug; `rag-grounding` is the feature/help topic.

## Are the calls async?

Yes — `execute` is a coroutine. `await` it or use
`asyncio.run`.

## Do I need attune-rag installed?

Yes — it's a core dependency. Without it the workflow raises a
`RuntimeError` pointing at `pip install attune-rag`.

## How do I control how much context is retrieved?

Set `k` (number of passages, default 3) and `depth` (turn /
budget tier).
