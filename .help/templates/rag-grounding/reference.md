---
type: reference
name: rag-grounding-reference
feature: rag-grounding
depth: reference
generated_at: 2026-05-21T03:20:54.627075+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG grounding reference

Generate code with citations to real attune APIs and documentation.

## Classes

| Class | Description |
|-------|-------------|
| `RagCodeGenWorkflow` | SDK-native RAG-grounded code generation workflow |

### RagCodeGenWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the RAG-grounded code generation |

## Constants

| Constant | Description |
|----------|-------------|
| `_SYSTEM_PROMPT` | System prompt that enforces grounding in attune documentation and prevents hallucination of non-existent features |

## Source files

- `src/attune/workflows/rag_code_gen.py`

## Tags

`rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
