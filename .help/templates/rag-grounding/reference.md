---
type: reference
feature: rag-grounding
depth: reference
generated_at: 2026-04-19T06:51:35.856464+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG grounding reference

Generate code grounded in retrieved context from the attune ecosystem. Prevents AI hallucination by citing real APIs, workflow names, and CLI commands.

## Classes

| Class | Description |
|-------|-------------|
| `RagCodeGenWorkflow` | Executes RAG-grounded code generation with context retrieval |

### RagCodeGenWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run code generation with retrieved context |

## Constants

| Constant | Description |
|----------|-------------|
| `_SYSTEM_PROMPT` | System prompt instructing the AI to ground responses in provided context |

## Source files

- `src/attune/workflows/rag_code_gen.py`

## Tags

`rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
