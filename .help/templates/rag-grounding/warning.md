---
type: warning
feature: rag-grounding
depth: warning
generated_at: 2026-04-19T06:51:50.850852+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG grounding cautions

## What to watch for

The RAG-grounded code generation workflow retrieves context from attune-help via attune-rag, then feeds citation-enforced prompts to Claude to generate answers with provenance tracking.

## Risk areas

**Hallucinated API references** — The system prompt explicitly prohibits inventing attune features, but if the retrieval context is incomplete or outdated, Claude may still generate plausible-looking but nonexistent APIs or workflow names.

**Context retrieval failures** — When attune-rag cannot find relevant context for a query, the workflow may proceed with minimal grounding, leading to generic responses that lack proper citations or attune-specific guidance.

**Citation drift** — Generated code may reference source files that have moved or been refactored since the RAG index was last updated, creating broken links in the provenance chain.

## How to avoid problems

1. **Verify generated API calls** — Before using code from `RagCodeGenWorkflow`, confirm that referenced classes, methods, and workflow names exist in current attune documentation or source code.

2. **Monitor retrieval quality** — If responses lack specific attune context or seem generic, check whether the underlying RAG system found relevant documents for your query.

3. **Keep RAG indices current** — Stale retrieval contexts lead to outdated citations and missing new features. Update your attune-rag index when the codebase changes significantly.

4. **Test with edge cases** — Try queries about rarely-used features or recent additions to verify that the grounding system can handle incomplete context gracefully.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
