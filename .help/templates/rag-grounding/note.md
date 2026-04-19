---
type: note
feature: rag-grounding
depth: note
generated_at: 2026-04-19T06:52:43.748144+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# Note: rag grounding

## Context

RAG-grounded code generation retrieves context from the attune help system via attune-rag, then feeds citation-enforced prompts to Claude. The workflow produces answers with clear provenance to prevent hallucinated features.

## Implementation

The feature centers on `RagCodeGenWorkflow`, which implements the SDK-native workflow pattern. The workflow enforces citation requirements through its system prompt: "You generate code and explanations grounded in the attune ecosystem. Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features. When referencing a pattern, note the source file it came from."

The workflow follows the standard execute pattern, taking keyword arguments and returning a `WorkflowResult`. This allows it to integrate with other attune workflows while maintaining the retrieval-grounding behavior.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
