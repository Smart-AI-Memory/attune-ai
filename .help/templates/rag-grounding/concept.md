---
feature: rag-grounding
depth: concept
generated_at: 2026-05-16T07:57:53.299579+00:00
source_hash: b292cc405776df72a1b9d1d8305fef86784d97ef15f9c68d9509bccecf1f865a
status: generated
---

# Rag Grounding

## How it works

RAG-grounded code generation — retrieves attune-help context via attune-rag, feeds citation-forced prompts to Claude, emits answers with provenance.

The main building blocks are:

- **`RagCodeGenWorkflow`** — SDK-native RAG-grounded code generation workflow.

## What connects to it

This feature relates to: rag, retrieval, grounding, faithfulness, citation.

Other parts of the codebase interact with
rag grounding through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RagCodeGenWorkflow` | SDK-native RAG-grounded code generation workflow. | `src/attune/workflows/rag_code_gen.py` |
