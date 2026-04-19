---
type: reference
feature: rag-grounding
depth: reference
generated_at: 2026-04-19T18:50:36.633522+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding reference

Generate code and explanations that cite real attune APIs, workflows, and CLI commands using retrieval-augmented generation.

## Classes

| Class | Description |
|-------|-------------|
| `RagCodeGenWorkflow` | Execute SDK-native RAG-grounded code generation workflow |

### RagCodeGenWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the RAG code generation workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the workflow and return results |

## Constants

| Constant | Description |
|----------|-------------|
| `_SYSTEM_PROMPT` | System prompt that enforces grounding in real attune features and prevents hallucination |

## Source files

- `src/attune/workflows/rag_code_gen.py`

## Tags

`rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
