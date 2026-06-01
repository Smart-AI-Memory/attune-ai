---
feature: rag-grounding
depth: concept
generated_at: 2026-06-01T11:59:09.454643+00:00
source_hash: 93cb0ee5d2aca6e29f80507cc0c23c2ba8b904fe0e64bf16403a5a0dd115ccef
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
