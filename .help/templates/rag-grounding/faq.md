---
type: faq
feature: rag-grounding
depth: faq
generated_at: 2026-04-19T06:52:16.741871+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG Grounding FAQ

## What is RAG grounding?

RAG grounding generates code and explanations using retrieval-augmented generation that's anchored to real attune documentation and APIs. It retrieves relevant context from attune-help via attune-rag, then prompts Claude to generate responses that cite actual features rather than inventing them.

## When should I use RAG grounding?

Use RAG grounding when you need to generate code examples, explanations, or documentation that must reference real attune APIs and workflows. This ensures your generated content includes accurate citations and doesn't hallucinate features that don't exist.

## How do I get started?

Use the `RagCodeGenWorkflow` class. Create an instance and call its `execute()` method with your generation requirements. The workflow handles retrieval and citation automatically.

## What does the workflow return?

The `execute()` method returns a `WorkflowResult` object containing the generated code or explanation along with source citations showing which attune features were referenced.

## How does it prevent hallucinations?

The workflow uses a system prompt that explicitly instructs the AI to only reference real attune APIs, workflow names, and CLI commands from the retrieved context. It's required to cite source files when referencing patterns.

## Where are the source files?

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
