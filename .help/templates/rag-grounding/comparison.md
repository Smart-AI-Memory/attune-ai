---
type: comparison
feature: rag-grounding
depth: comparison
generated_at: 2026-04-19T18:51:56.161333+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding vs direct LLM code generation

RAG-grounded code generation retrieves attune-help context via attune-rag, feeds citation-forced prompts to Claude, and emits answers with provenance. This comparison helps you decide when grounding is worth the overhead versus calling an LLM directly.

## Feature comparison

| Capability | RAG grounding | Direct LLM |
|---|---|---|
| **Response accuracy** | High for attune ecosystem questions | Varies; can hallucinate attune-specific APIs |
| **Citation tracking** | Built-in provenance links to source docs | No citations; user must verify claims |
| **Setup complexity** | Requires attune-rag retrieval pipeline | Single LLM API call |
| **Response latency** | ~2-3x slower due to retrieval step | Fast; direct model inference |
| **Context freshness** | Always uses latest attune-help content | Training data may be months stale |
| **Cost per query** | Higher (retrieval + generation tokens) | Lower (generation tokens only) |
| **Offline capability** | Requires network for both retrieval and LLM | Can work with local models |

## When to use RAG grounding

Use `RagCodeGenWorkflow` when you need **verifiable answers about the attune ecosystem**:

- Generating code that uses attune APIs, workflows, or CLI commands
- Answering questions about attune features where accuracy matters more than speed
- Building user-facing tools that must cite their sources
- Working with developers who are new to attune and need guided examples

The system prompt enforces citation requirements: "Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features."

## When to use direct LLM calls

Choose direct LLM generation when you need **speed over verification**:

- Prototyping or exploratory coding where accuracy is less critical
- General programming questions unrelated to attune specifics
- Batch processing where retrieval latency would be prohibitive
- Working offline or in environments where retrieval isn't available

## Recommendation

**Start with RAG grounding** for any attune-related code generation. The citation overhead pays for itself by preventing hallucinated APIs that waste debugging time. Switch to direct LLM calls only when you've confirmed the speed difference matters for your use case.

For mixed workloads, use RAG grounding for attune-specific queries and direct calls for general programming questions.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
