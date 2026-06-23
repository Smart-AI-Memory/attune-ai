---
type: tip
name: rag-grounding-tip
feature: rag-grounding
depth: tip
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
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
