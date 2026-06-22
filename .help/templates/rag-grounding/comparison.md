---
type: comparison
name: rag-grounding-comparison
feature: rag-grounding
depth: comparison
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 88333793edaf078345820f76455b27a1c759145c2e48dd64da93abf6f2d61450
status: generated
---

# Comparison: RAG-grounded code generation vs alternatives

## What RAG grounding does

`RagCodeGenWorkflow` retrieves attune-help context, feeds citation-forced prompts to Claude, and emits answers with source provenance. Every claim in the output traces back to a real attune API, workflow name, or CLI command — the system prompt explicitly forbids inventing attune features.

That design makes it the right choice for some problems and the wrong choice for others.

## Feature comparison

| Capability | `RagCodeGenWorkflow` | Direct LLM call (no RAG) | Throwaway script |
|---|---|---|---|
| Cites real attune APIs and workflow names | ✅ Always — citation is enforced by the system prompt | ❌ Model may hallucinate feature names | ❌ N/A |
| Output grounded in attune-help documentation | ✅ Retrieved at call time | ❌ Depends on training data cutoff | ❌ N/A |
| Resists prompt injection in retrieved passages | ✅ `<passage>` content is treated as data, not instructions | ❌ No such boundary | ❌ N/A |
| Setup overhead | Medium — `RagCodeGenWorkflow.__init__` accepts config via `**kwargs` | Low — one API call | None |
| Useful for one-off exploration | No — wiring up the workflow adds ceremony with little benefit | Maybe | ✅ Best fit |
| Returns structured `WorkflowResult` | ✅ | ❌ | ❌ |

## Tradeoffs to know before choosing

**`RagCodeGenWorkflow` is the right default when faithfulness matters.** The citation-forced prompt means the model cannot silently invent an attune workflow or API name. That guarantee costs you retrieval latency and the overhead of calling `execute(**kwargs)` through the workflow interface — a direct LLM call will be faster when you do not need grounding.

**A direct LLM call is faster but unsafe for attune-specific output.** If you ask an ungrounded model to generate code that references attune internals, it will produce plausible-looking but potentially fictional names. Use an ungrounded call only when the task is generic enough that attune-specific accuracy is not required.

**A throwaway script beats both when you are still exploring.** The workflow is purpose-built for production-quality, cited answers. If you are spiking an idea and do not yet know whether attune-help context is relevant, a plain script avoids the overhead of configuring `RagCodeGenWorkflow` for a single use.

## Use `RagCodeGenWorkflow` when…

- You need generated code or explanations that cite real attune APIs, workflow names, or CLI commands — not plausible inventions.
- Downstream consumers of the output need to verify claims against source documentation.
- You want injection-safe handling of retrieved documentation (the system prompt ignores directives inside `<passage>` tags).
- You are working within the attune SDK and want a structured `WorkflowResult` back rather than raw model output.

## Do not use `RagCodeGenWorkflow` when…

- Your task is generic (not attune-specific) and grounding adds latency with no accuracy benefit — a direct LLM call is simpler.
- You are doing early exploratory work where the shape of the problem is still unclear — wire up the workflow once you know you need cited output.
- You need behavior the `execute` method does not expose — do not patch internals; propose an extension point instead.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
