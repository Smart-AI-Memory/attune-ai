---
type: error
feature: rag-grounding
depth: error
generated_at: 2026-04-19T06:51:40.710748+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG grounding errors

RAG grounding failures occur when the retrieval-augmented generation workflow cannot properly retrieve context from attune-help, generate code with Claude, or enforce citation requirements.

## Common error signatures

- `WorkflowResult` execution errors from malformed `**kwargs` in `RagCodeGenWorkflow.execute()`
- Context retrieval failures when attune-rag service is unavailable
- Citation validation errors when Claude generates responses without proper source attribution
- Prompt construction failures when the system prompt cannot be properly formatted with retrieved context

## Where errors originate

Errors in RAG grounding originate from the `RagCodeGenWorkflow` class in `src/attune/workflows/rag_code_gen.py`. Check these methods based on your error:

- `__init__()` — Configuration and initialization problems
- `execute()` — Runtime workflow execution failures, context retrieval issues, or LLM response problems

## How to diagnose

1. **Check the workflow kwargs.** The `execute()` method accepts `**kwargs` that configure retrieval and generation. Verify that required parameters are present and properly typed.

2. **Verify attune-rag connectivity.** RAG grounding depends on the attune-rag service for context retrieval. Connection failures will prevent the workflow from accessing relevant documentation and code examples.

3. **Inspect citation enforcement.** The system prompt requires Claude to "cite real APIs, workflow names, and CLI commands" and "never invent attune features." Check if the generated response includes proper source file citations as required.

4. **Examine context quality.** Poor retrieval results can cause Claude to generate responses that violate the grounding constraints. Review the retrieved context to ensure it contains relevant attune ecosystem information.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
