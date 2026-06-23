---
type: reference
name: rag-grounding-reference
feature: rag-grounding
depth: reference
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Reference

The public surface is `RagCodeGenWorkflow`, re-exported from
`attune.workflows`.

### `RagCodeGenWorkflow` — `attune.workflows.rag_code_gen`

| Symbol | Purpose |
|--------|---------|
| `RagCodeGenWorkflow(**kwargs)` | Construct the workflow (pipeline is lazily initialized on first `execute`). |
| `RagCodeGenWorkflow.execute(**kwargs)` | **Async.** Retrieve + generate. Honors `query` (required), `k`, `depth`, `feedback`, `model`, `path` (and deprecated `cwd`). Returns a `WorkflowResult`. |
| `RagCodeGenWorkflow.name` | The registered CLI slug, `"rag-code-gen"`. |
| `RagCodeGenWorkflow.stages` | `["retrieve", "generate"]` — retrieve at `CHEAP` (zero-LLM), generate at `CAPABLE`. |

### Depth → turns and budget

| Depth | Max turns | Budget cap | Notes |
|-------|-----------|------------|-------|
| `quick` | 6 | $2 | Narrowest, cheapest. |
| `standard` | 12 | $10 | Default. |
| `deep` | 24 | $25 | Enables extended thinking. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | Generated answer followed by a `## Sources` citations block. |
| `summary` | `str \| None` | Short overview. |
| `metadata` | `dict` | `query`, `depth`, `max_turns`, `citation` (structured provenance), `fallback_used`, `confidence`, `retrieval_ms`, `feedback_recorded`. |
| `error` | `str \| None` | Failure reason (e.g. missing `query`, bad `k`, unknown `model`, RAG retrieval failure). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python | `await RagCodeGenWorkflow().execute(query=<q>, k=<n>, depth=<d>)`. |
| CLI | `attune workflow run rag-code-gen --input '{"query": "<q>"}' [--depth ...] [--json]`. |
| Skill | `/rag-code-gen` in a Claude Code conversation. |

There is no dedicated MCP tool for this workflow.
