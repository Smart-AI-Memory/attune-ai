---
type: concept
feature: rag-grounding
depth: concept
generated_at: 2026-05-04T02:41:31.343503+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG grounding

RAG grounding ensures that AI-generated code and explanations reference real attune features rather than hallucinated ones. It retrieves documentation context through attune-rag, then forces the language model to cite actual APIs, workflow names, and CLI commands from the retrieved sources.

## Core mechanism

When you request code generation, the RAG grounding workflow follows a three-step process:

1. **Retrieval** — queries the attune-help documentation to find relevant context for your request
2. **Prompt construction** — injects retrieved context into a system prompt that explicitly forbids invention of attune features
3. **Citation enforcement** — requires the language model to note source files when referencing patterns or APIs

The system prompt ensures faithfulness to real attune capabilities: "You generate code and explanations grounded in the attune ecosystem. Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features. When referencing a pattern, note the source file it came from."

## Implementation

The `RagCodeGenWorkflow` class provides the SDK interface for RAG-grounded generation. You instantiate it and call `execute()` with your code generation parameters. The workflow returns a `WorkflowResult` that includes both the generated code and the source files it referenced.

This approach solves the common problem where language models confidently describe non-existent APIs or suggest outdated patterns. By grounding generation in current documentation, you get answers that work with the actual attune codebase.
