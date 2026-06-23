# Smart Test

## Overview

Smart-test answers two questions about your test suite: *what isn't
tested?* and *what tests would close the gap?* It pairs two
SDK-native workflows:

- **test-audit** (`TestAuditWorkflow`) — a coverage audit that
  finds untested and under-tested code and prioritizes it;
- **test-gen** (`TestGenerationWorkflow`) — test generation that
  writes pytest tests with edge cases and error paths.

A third workflow, **`ParallelTestGenerationWorkflow`**, batches
generation across many low-coverage modules at once. Each of the
two primary workflows is SDK-native: it delegates to three
specialized Claude Agent SDK subagents (scoped to Read / Glob /
Grep) and synthesizes their findings into a single
`WorkflowResult`.

Like the other analysis workflows, the audit **predicts** — its
findings are LLM judgments to verify, not proofs — and generated
tests are a **starting point** to review and run, not guaranteed-
passing code.

You reach smart-test several ways:

- the **`/smart-test`** skill, inside a Claude Code conversation —
  a router for *gap analysis*, *test generation*, or *both* (see
  *The `/smart-test` skill routes by approach* below);
- the CLI — **`attune workflow run test-audit`** and
  **`attune workflow run test-gen`**;
- MCP tools — **`test_audit`** and **`test_gen_parallel`**;
- the Python API — `await TestAuditWorkflow().execute(...)`,
  `await TestGenerationWorkflow().execute(...)`, and
  `await ParallelTestGenerationWorkflow().execute(...)`.

A name note: the **feature, skill, and help topic** are
`smart-test`, but the two workflows it drives register under the
slugs **`test-audit`** and **`test-gen`**. There is also a
**separate, unrelated** repo-level skill at
`.claude/skills/smart-test` (alias `st`) that just runs the
pytest tests affected by your recent diff — same name, different
job. This page documents the gap-analysis-and-generation feature.

## Concepts

### Audit, then generate

The two primary workflows compose: run the audit to find and rank
gaps, then run generation to write the tests that close them.

| Workflow | Slug | Subagents | What it produces |
|----------|------|-----------|------------------|
| `TestAuditWorkflow` | `test-audit` | `coverage-auditor`, `gap-analyzer`, `test-planner` | A coverage report: health score, coverage metrics, untested paths, and a prioritized plan. |
| `TestGenerationWorkflow` | `test-gen` | `function-identifier`, `test-designer`, `test-writer` | A report of generated pytest tests covering happy paths, edge cases, and error handling. |

Both synthesize their three passes into a report with the same
four sections — **Summary** (an overall 0–100 health score plus a
short executive summary), **Coverage**, **Test Gaps**, and
**Suggestions** (next steps ordered by priority).

### Depth controls the agent-turn budget

Both workflows take a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`, which maps to the maximum agent turns and a per-run
cost cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20 turns).

### `execute` is async

On both workflows `execute` is a coroutine — `await` it (or drive
it with `asyncio.run`). Each reads `path` (required) and `depth`
(default `"standard"`); an empty or missing `path` returns a failed
`WorkflowResult` ("path argument is required") rather than raising.
`TestAuditWorkflow.execute` also accepts a deprecated `src_path`
alias for `path` (it emits a `DeprecationWarning` and `path` wins
if both are given).

### Batch generation across many modules

`ParallelTestGenerationWorkflow` (registered name
`parallel-test-generation`) is the batch path: its `execute` takes
`top` (number of lowest-coverage modules to process, default
`200`), `batch_size` (modules generated in parallel, default `10`),
and `output_dir` (where tests are written, default
`tests/behavioral/generated`). It discovers the lowest-coverage
modules, generates a test template and completes it per module, and
returns a `WorkflowResult` with the generated file paths and
statistics. Unlike test-audit / test-gen it is a multi-stage
pipeline (`discover` → `generate_templates` → `complete_tests` →
`validate`), not a single SDK query.

### The result is a `WorkflowResult`

Each `execute` returns a `WorkflowResult` (from
`attune.workflows`). The report lands in `final_output` — a
serialized report when the findings parse, or the raw markdown
otherwise — with a short `summary`, a `suggestions` list, the
`cost_report`, the `provider`, and a `metadata` dict echoing the
run's `path` (or `src_path` for the audit), `depth`, and
`max_turns`. On failure, `success` is `False` and `error` /
`error_type` carry the reason.

### The `/smart-test` skill routes by approach

The `/smart-test` skill picks the tool for the approach you ask
for:

- **Gap analysis** → the audit (find untested public functions);
- **Generate tests** → test generation for a module;
- **Both** → audit first, then generate for the gaps it found.

The CLI and Python surfaces, by contrast, drive each workflow
directly.

## Design & extension

### Design decisions

- **Two SDK-native workflows, one feature.** Finding gaps and
  writing tests are separable concerns, so smart-test keeps them as
  two workflows — `test-audit` and `test-gen` — each a single
  `claude_agent_sdk.query` with three focused subagents. The
  `/smart-test` skill composes them.
- **A separate batch path for scale.** `ParallelTestGenerationWorkflow`
  is a multi-stage pipeline (discover → template → complete →
  validate) rather than one SDK query, because batch generation
  across hundreds of modules is a different shape from a single
  focused pass.
- **Prediction and drafts, not certification.** The audit returns
  LLM-judged findings; generation returns draft tests. Both are
  inputs to verify, never guarantees.
- **The result is data, not print output.** Each `execute` returns
  a `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI, MCP, and
  Python surfaces render that same result.

### Extension points

- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) on the audit or generation workflow.
- **Scope the run:** point `path` at a narrower directory or file.
- **Tune the batch run:** set `top`, `batch_size`, and `output_dir`
  on `ParallelTestGenerationWorkflow.execute`.
- **Add a subagent pass:** the subagent definitions live in each
  workflow module (`test_audit/workflow.py`, `test_gen/workflow.py`)
  with the names in `_SUBAGENT_NAMES`; a new pass is a new
  `AgentDefinition` plus a synthesis section in the task template.

<!-- attune-generated: source_hash=d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe feature=smart-test kind=architecture generated_at=2026-06-23 -->
