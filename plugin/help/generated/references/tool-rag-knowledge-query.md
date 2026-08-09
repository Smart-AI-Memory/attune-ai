---
type: reference
subtype: tabular
name: tool-rag-knowledge-query
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Rag Knowledge Query

Query the RAG knowledge corpus (attune-help by default) for a given question. Returns ranked hits plus an augmented prompt string ready to feed to any LLM. Does NOT call an LLM itself — use the rag-code-gen workflow for end-to-end generation.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `query` | string | The question or request to ground against the corpus |  | required |
| `k` | integer | Max hits to return (1-10) |  | 3 |

## Usage

`rag_knowledge_query(query="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Discovery Sweep — Run the discovery-sweep meta-workflow: fans out across all a...
