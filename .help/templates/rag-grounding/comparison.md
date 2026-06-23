---
type: comparison
name: rag-grounding-comparison
feature: rag-grounding
depth: comparison
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
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
