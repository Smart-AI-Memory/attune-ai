---
type: reference
name: rag-grounding-reference
feature: rag-grounding
depth: reference
generated_at: 2026-06-02T10:56:02.685870+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
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
