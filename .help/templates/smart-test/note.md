---
type: note
name: smart-test-note
feature: smart-test
depth: note
generated_at: 2026-06-23T15:57:46.208360+00:00
source_hash: d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe
status: generated
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

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

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  the three workflow classes and their async `execute`, plus the
  `WorkflowResult` they return. Internal helpers (underscore-
  prefixed names, the AST/coverage parsing utilities) may change.
- **Audit before you generate.** Running `test-audit` first tells
  you *where* the gaps are so a `test-gen` pass spends its budget on
  the modules that matter.
- **Keep runs cheap with `path` and `depth`.** A `quick` pass over
  one module is far faster than a `deep` pass over `src/`.
- **Single-module generation is most reliable via CLI / Python.**
  Drive it with `attune workflow run test-gen --path <module>` or
  `TestGenerationWorkflow().execute(path=<module>)`.
