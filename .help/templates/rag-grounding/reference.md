---
type: reference
name: rag-grounding-reference
feature: rag-grounding
depth: reference
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 88333793edaf078345820f76455b27a1c759145c2e48dd64da93abf6f2d61450
status: generated
---

# RAG grounding reference

Retrieve attune-help context, feed citation-forced prompts to Claude, and emit answers with provenance.

## Classes

| Class | Description |
|-------|-------------|
| `RagCodeGenWorkflow` | SDK-native RAG-grounded code generation workflow. |

### `RagCodeGenWorkflow`

**Module:** `workflows.rag_code_gen`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initializes the workflow. |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Runs the RAG-grounded code generation workflow. |

## Constants

| Constant | Type | Description |
|----------|------|-------------|
| `_SYSTEM_PROMPT` | `str` | System prompt that grounds code generation in the attune ecosystem. Instructs the model to cite real APIs, workflow names, and CLI commands; prohibits inventing attune features; treats content inside `<passage>…</passage>` tags as retrieved documentation, never as directives. |

## Source files

- `src/attune/workflows/rag_code_gen.py`

## Tags

`rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
