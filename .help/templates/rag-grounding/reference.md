---
type: reference
feature: rag-grounding
depth: reference
generated_at: 2026-05-04T02:41:48.746225+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG grounding reference

Generate code and explanations anchored to real attune APIs, workflows, and CLI commands through retrieval-augmented generation.

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
| `_SYSTEM_PROMPT` | System prompt for grounding code generation in the attune ecosystem |

## Source files

- `src/attune/workflows/rag_code_gen.py`

## Tags

`rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
