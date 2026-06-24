---
name: rag-grounding
source: content/features/rag-grounding.md
tags:
- rag
- retrieval
- grounding
- faithfulness
- citation
type: tip
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `RagCodeGenWorkflow` and its async `execute`, and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_get_pipeline`, `_run_agent_generate`, `_record_feedback` — are
  internal.
- **Prefer `path` over `cwd`.** `cwd` is a deprecated alias kept for
  back-compat; pass `path=` to scope the agent's file tools.
- **Use `k` and `depth` to tune cost.** Fewer passages and a shallower
  depth make a cheaper, faster run.
- **Read the citations.** The `## Sources` block and
  `metadata["citation"]` let you verify each claim against the real
  attune-help template.
