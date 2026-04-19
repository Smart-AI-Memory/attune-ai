---
type: concept
feature: rag-grounding
depth: concept
generated_at: 2026-04-19T18:50:18.591539+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding

RAG grounding ensures code generation answers cite real attune features and APIs instead of hallucinating capabilities that don't exist.

## How it works

When you ask for code generation, the system first retrieves relevant context from attune-help documentation using the RAG (Retrieval-Augmented Generation) pipeline. This context gets passed to Claude with a citation-enforcing system prompt that explicitly forbids inventing features. The result is generated code with provenance—each suggestion links back to the documentation that supports it.

The workflow runs through `RagCodeGenWorkflow`, which combines retrieval and generation into a single executable step. You call `execute()` with your request, and it returns both the generated code and the source files that informed the response.

## Citation enforcement

The system prompt includes specific instructions that prevent hallucination: *"Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features. When referencing a pattern, note the source file it came from."*

This means generated code won't reference non-existent functions or suggest workflow patterns that aren't actually available in the attune ecosystem.

## When to use RAG grounding

Use RAG-grounded generation when you need code suggestions that you can trust to work with the actual attune codebase. Without grounding, language models tend to generate plausible-looking but incorrect API calls or reference features that don't exist.

The grounded approach trades some creative freedom for factual accuracy—useful when you're building production workflows rather than exploring hypothetical approaches.
