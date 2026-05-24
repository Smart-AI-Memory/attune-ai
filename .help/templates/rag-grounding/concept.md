---
type: concept
name: rag-grounding-concept
feature: rag-grounding
depth: concept
generated_at: 2026-05-21T03:20:54.610898+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG Grounding

RAG grounding is a code generation approach that retrieves relevant documentation from attune-help before generating code, ensuring all outputs are backed by real attune ecosystem APIs and patterns.

## How RAG grounding works

When you ask for code or explanations, the system first searches attune-help documentation for relevant context. This retrieved content is then passed to Claude along with your request, but with strict instructions to only reference what's actually documented. The result is generated code that cites real APIs, workflow names, and CLI commands rather than inventing features.

The grounding process prevents hallucination by:

1. **Retrieval first** — attune-rag searches the help system for content matching your request
2. **Context injection** — retrieved passages are embedded in the prompt as `<passage>...</passage>` blocks
3. **Citation forcing** — Claude receives explicit instructions to ground all responses in the provided context
4. **Provenance tracking** — generated answers include references to the source files where patterns originated

## Core components

**`RagCodeGenWorkflow`** orchestrates the entire process. This SDK-native workflow takes your request, retrieves relevant documentation through attune-rag, constructs a grounded prompt, and returns generated code with citations.

The workflow uses a system prompt (`_SYSTEM_PROMPT`) that specifically instructs Claude to treat passage content as documentation rather than commands, preventing prompt injection attacks where malicious content might try to override the grounding instructions.

## When to use RAG grounding

RAG grounding is essential when you need generated code that integrates with the attune ecosystem. Unlike general-purpose code generation, it ensures that:

- API calls use real method signatures from attune
- Workflow references point to actual workflow classes
- CLI commands match the current attune interface
- Code patterns follow documented attune conventions

This makes RAG grounding particularly valuable for onboarding new developers, generating integration examples, and creating documentation that stays synchronized with the codebase.
