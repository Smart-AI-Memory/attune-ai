---
type: concept
feature: rag-grounding
depth: concept
generated_at: 2026-04-19T06:51:17.806434+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG Grounding

RAG grounding generates code responses by retrieving relevant context from the attune ecosystem and requiring citations to real APIs, workflows, and CLI commands.

## How it works

The workflow combines retrieval-augmented generation with citation enforcement to prevent hallucination. When you request code generation, the system first retrieves relevant context from attune documentation and existing code patterns using the `attune-rag` system. It then prompts Claude with this context alongside specific instructions to cite real features and note source files for any patterns referenced.

The system prompt enforces this grounding: "You generate code and explanations grounded in the attune ecosystem. Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features. When referencing a pattern, note the source file it came from."

## Core component

**`RagCodeGenWorkflow`** implements the SDK-native workflow that orchestrates retrieval, prompt construction, and response generation. You can execute it through the standard workflow interface to get code suggestions that maintain fidelity to the actual attune codebase.

## Integration points

Other parts of the codebase interact with RAG grounding through:

| Interface | Purpose | File |
|-----------|---------|------|
| `RagCodeGenWorkflow` | SDK-native RAG-grounded code generation workflow | `src/attune/workflows/rag_code_gen.py` |
