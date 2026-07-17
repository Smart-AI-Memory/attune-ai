---
name: rag-code-gen
description: "RAG-grounded code generation with source citations. Triggers on: grounded code, ground this, cite sources, show me with sources, how do I with attune, reference attune docs, grounded against attune docs."
---
# RAG-grounded code generation

attune-rag ships with attune-ai core (`pip install attune-ai`).
Grounds code generation in the attune-help template corpus
so outputs cite real APIs, workflow names, and patterns
instead of hallucinating them. Every output ends with a
`## Sources` block of clickable citations.

## Scoping

Before running, ask:

1. **What are you trying to produce?** Code, config,
   explanation, or a mix?
2. **Any specific attune surface?** e.g. "the
   security-audit workflow", "MCP tool pattern", "BaseWorkflow
   subclass". Helps retrieval hit the right concept file.
3. **Depth?** Default is `standard`. `quick` saves time
   and budget for simple asks; `deep` is for complex
   multi-file or architectural questions.

## Running

```
attune workflow run rag-code-gen \
  --input '{"query": "<the request>"}'
```

Optional inputs:

- `k` — max grounding docs to retrieve (default 3)
- `depth` — `quick` / `standard` / `deep`
- `feedback` — pass `good` or `bad` AFTER inspecting the
  output to record a verdict against every cited template
- `model` — override the generator model if you need to

## Output shape

`WorkflowResult.final_output` is a string with two parts:

1. The generated code / explanation
2. A `## Sources` section listing each cited
   `attune-help` template with its category, retrieval
   score, and a clickable link to the source on GitHub

`WorkflowResult.metadata` carries the full citation dict
(`query`, `retriever_name`, `retrieved_at`, `hits[]`) plus
`fallback_used` and `confidence` so callers can make
routing decisions.

## When RAG doesn't help

If the retriever can't find relevant templates, the
workflow still runs — it falls back to an unaugmented
prompt that explicitly tells the model there is NO
grounding context so it should say "I don't know about
attune X" rather than invent. `metadata.fallback_used` is
`True` in that case.

## Alternative: MCP tool only (no LLM call)

If you want just retrieval without generation, use the
`rag_knowledge_query` MCP tool directly. It returns hits +
an augmented prompt string without calling an LLM itself —
handy for routing decisions, agent planning, or feeding
another model.

## If the extra isn't installed

The workflow returns a structured error pointing at
`pip install attune-rag` (a core dep — missing means a broken
install). No exception propagates.

## See also

- [docs/rag/index.md](../../docs/rag/index.md) — full
  walkthrough including the standalone attune-rag usage
- [attune-rag on PyPI](https://pypi.org/project/attune-rag/)
- [Embeddings decision record](../../docs/rag/embeddings-decision-2026-04-17.md)
