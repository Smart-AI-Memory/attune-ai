---
type: comparison
feature: rag-grounding
depth: comparison
generated_at: 2026-04-19T06:52:49.567894+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# RAG grounding vs other code generation approaches

## What is RAG grounding

RAG grounding retrieves relevant context from attune documentation via attune-rag, then feeds citation-forced prompts to Claude. The system enforces that generated code references real APIs, workflow names, and CLI commands from the attune ecosystem rather than inventing features.

The core implementation is `RagCodeGenWorkflow`, which combines retrieval and generation in a single SDK-native workflow.

## Feature comparison

| Aspect | RAG grounding | Standard LLM prompting | Manual documentation lookup |
|--------|---------------|----------------------|---------------------------|
| **Accuracy** | High - enforced citations from real docs | Low - prone to hallucination | High - human verification |
| **Speed** | Medium - retrieval + generation | Fast - direct generation | Slow - manual research |
| **Provenance** | Built-in source attribution | None | Manual tracking |
| **Maintenance** | Auto-updates with doc changes | Requires prompt engineering | Constant manual updates |
| **Scope** | Limited to attune ecosystem | Unlimited but unreliable | Limited by human capacity |

## Use RAG grounding when

- You need code examples that reference actual attune APIs
- Provenance and citation accuracy matter for your use case
- You're building documentation, tutorials, or help systems
- You want to avoid the hallucination risks of unconstrained LLM generation
- Your workflow can tolerate the retrieval latency overhead

## Don't use RAG grounding when

- You need general-purpose code generation outside the attune ecosystem
- Speed matters more than accuracy (RAG retrieval adds ~2-3x latency)
- You're prototyping and don't need real API references
- Your use case requires inventing new APIs or patterns not in the documentation
- You need interactive code completion (this is a batch-oriented workflow)

## Alternative approaches

**Standard LLM prompting**: Faster but unreliable for attune-specific code. Use for general programming tasks where hallucination risk is acceptable.

**Manual documentation lookup**: Most accurate but doesn't scale. Use for one-off questions or when you need to understand complex architectural decisions.

**Hybrid approach**: Start with RAG grounding for the foundation, then iterate with standard prompting for refinement. This gives you accurate scaffolding with flexible iteration.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
