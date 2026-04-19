---
type: faq
feature: rag-grounding
depth: faq
generated_at: 2026-04-19T18:51:22.593931+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding FAQ

## What is RAG grounding?

RAG grounding retrieves context from attune-help documentation using attune-rag, then feeds that context to Claude with citation-enforced prompts. The result is code generation that cites real APIs and workflow names instead of inventing features.

## When should I use RAG grounding?

Use RAG grounding when you need to generate code that references the attune ecosystem accurately. It prevents Claude from hallucinating non-existent APIs or workflow patterns by grounding responses in actual documentation.

## How do I create a RAG-grounded workflow?

Instantiate `RagCodeGenWorkflow` from `src/attune/workflows/rag_code_gen.py` and call its `execute` method. The workflow handles retrieval and prompt construction automatically.

## What makes RAG grounding different from regular code generation?

Regular code generation relies on Claude's training data, which may be outdated or inaccurate for attune-specific features. RAG grounding injects current documentation context into each request, ensuring generated code references actual APIs and follows documented patterns.

## Why does my generated code include source file citations?

The system prompt forces citations to maintain provenance. When the generated code references a pattern or API, you can trace it back to the specific documentation file where that information originated.

## How do I debug RAG grounding issues?

Run `pytest -k "rag-grounding" -v` first. If tests pass but your workflow fails, add `logger.debug` statements at suspected failure points and re-run with logging enabled to trace the retrieval and generation process.

## Where is the RAG grounding code?

The main implementation is in `src/attune/workflows/rag_code_gen.py` with the `RagCodeGenWorkflow` class.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
