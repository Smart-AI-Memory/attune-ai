---
type: note
feature: rag-grounding
depth: note
generated_at: 2026-04-19T18:51:46.076914+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# Note: RAG grounding

## Context

RAG (Retrieval-Augmented Generation) grounding addresses the hallucination problem in AI code generation. When you ask an AI assistant to write code using a specific framework or API, it often invents methods, classes, or patterns that don't exist. RAG grounding solves this by first retrieving relevant documentation from the actual codebase, then constraining the AI's response to only use verified information.

## How it works

The attune ecosystem implements RAG grounding through a workflow that retrieves context from attune-help documentation before generating responses. The system uses a citation-forcing prompt template that requires Claude to ground every API reference, workflow name, and CLI command in the provided context.

The core implementation lives in `RagCodeGenWorkflow`, which orchestrates the retrieval and generation phases. When you request code that uses attune features, the workflow first queries the help system for relevant documentation, then feeds both your request and the retrieved context to Claude with explicit instructions not to invent capabilities.

## Why this matters

Without grounding, AI assistants confidently suggest non-existent APIs, leading to code that won't compile or run. With RAG grounding, responses include provenance — you can verify every suggested method or pattern by checking the source file it references. This builds trust and reduces debugging time when following AI-generated guidance.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
