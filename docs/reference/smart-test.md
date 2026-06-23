# Smart Test

## Reference

Smart-test's public surface is the `TestAuditWorkflow`,
`TestGenerationWorkflow`, and `ParallelTestGenerationWorkflow`
classes, re-exported from `attune.workflows`. `WorkflowResult`
comes from `attune.workflows` as well.

### Workflow classes

| Symbol | Purpose |
|--------|---------|
| `TestAuditWorkflow.execute(**kwargs)` | **Async.** Coverage audit. Honors `path` (str, required; deprecated `src_path` alias) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). Slug `"test-audit"`. |
| `TestGenerationWorkflow.execute(**kwargs)` | **Async.** Test generation. Honors `path` (str, required) and `depth` (default `"standard"`). Slug `"test-gen"`. |
| `ParallelTestGenerationWorkflow.execute(top=200, batch_size=10, output_dir="tests/behavioral/generated")` | **Async.** Batch generation across low-coverage modules. Registered name `"parallel-test-generation"`. |

Each `test-audit` / `test-gen` stage runs at the `CAPABLE` model
tier. Underscore-prefixed names (`_run_agent_audit`,
`_run_agent_gen`, `_SUBAGENT_NAMES`) are internal and may change.

### Depth → agent-turn budget (test-audit / test-gen)

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest pass on a large or critical area. |

### Subagents

| Workflow | Subagents |
|----------|-----------|
| `test-audit` | `coverage-auditor` (coverage metrics), `gap-analyzer` (untested paths), `test-planner` (prioritized plan). |
| `test-gen` | `function-identifier` (finds untested functions), `test-designer` (designs cases), `test-writer` (writes pytest code). |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | The report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"` for the SDK workflows). |
| `metadata` | `dict` | Echoes the run's `path` / `src_path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/smart-test` in a Claude Code conversation — routes to gap analysis, generation, or both. |
| CLI | `attune workflow run test-audit --path <p> [--depth ...] [--json]`; `attune workflow run test-gen --path <p> [--depth ...] [--json]`. |
| MCP tools | `test_audit` (optional `path`, defaults to `src/`); `test_gen_parallel` (`top`, `batch_size`). |
| Python | `await TestAuditWorkflow().execute(path=<p>)`; `await TestGenerationWorkflow().execute(path=<p>)`; `await ParallelTestGenerationWorkflow().execute(top=..., batch_size=...)`. |

For single-module test generation, the reliable surfaces are the
CLI (`attune workflow run test-gen --path <module>`) and the Python
API (`TestGenerationWorkflow().execute(path=<module>)`).

<!-- attune-generated: source_hash=d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe feature=smart-test kind=reference generated_at=2026-06-23 -->
