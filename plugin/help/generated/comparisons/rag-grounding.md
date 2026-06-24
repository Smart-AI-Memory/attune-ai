---
name: rag-grounding
source: content/features/rag-grounding.md
tags:
- rag
- retrieval
- grounding
- faithfulness
- citation
type: comparison
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Comparison

RAG grounding is the **citation-forced generation** workflow. It is
distinct from a plain code-generation call and from documentation
retrieval:

| Tool | Role |
|------|------|
| `rag-grounding` (this feature, slug `rag-code-gen`) | Retrieve attune context, then generate a cited answer. |
| `doc-gen` | Generate documentation from your source code (no RAG retrieval). |
| `rag_knowledge_query` (MCP) | Query the attune-help corpus directly, without an LLM generation step. |

Reach for **rag-grounding** when you want a generated answer that cites
real attune APIs/CLI/workflows; reach for `rag_knowledge_query` when
you just want the retrieved passages.
