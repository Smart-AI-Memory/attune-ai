---
feature: smart-test
summary: Find untested code with a coverage audit, then generate pytest tests to close the gaps
tags: [tests, coverage, generation]
source_globs:
  - src/attune/workflows/test_audit/**
  - src/attune/workflows/test_gen/**
  - src/attune/workflows/test_gen_parallel.py
nav:
  help: smart-test
  mkdocs:
    how-to: how-to/smart-test
    architecture: architecture/smart-test
    reference: reference/smart-test
---

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

## Quickstart

Audit a directory for coverage gaps and print the report.
`TestAuditWorkflow.execute` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import TestAuditWorkflow


async def main() -> None:
    workflow = TestAuditWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed audit
    print(result.summary)          # short coverage summary
    print(result.final_output)     # the full gap report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest audit.

## Tasks

### Find coverage gaps from the CLI

**Goal:** audit a directory for untested code without writing any
Python.

**Steps:**

```bash
# Audit a source tree at the default (standard) depth:
attune workflow run test-audit --path src/

# Deep audit, JSON output for a CI gate:
attune workflow run test-audit --path src/ --depth deep --json
```

**Verify:** the audit slug is `test-audit`. `--path` / `-p`
defaults to the current directory; `--depth` accepts `quick`,
`standard`, or `deep`; `--json` / `-j` emits machine-readable
output. Use `attune workflow info test-audit` to confirm
registration.

### Generate tests for a module from the CLI

**Goal:** write pytest tests for a module that came back
under-covered.

**Steps:**

```bash
# Generate tests for a single module:
attune workflow run test-gen --path src/attune/config.py

# A deeper generation pass:
attune workflow run test-gen --path src/attune/config.py --depth deep
```

**Verify:** the generation slug is `test-gen`. It takes the same
`--path` / `--depth` / `--json` flags as the audit. Review and run
the generated tests before committing them — generation is a
starting point, not guaranteed-passing code.

### Audit then generate from Python

**Goal:** drive the find-then-fill loop from a script.

**Steps:**

```python
import asyncio

from attune.workflows import TestAuditWorkflow, TestGenerationWorkflow


async def main() -> None:
    audit = await TestAuditWorkflow().execute(path="src/api/")
    if not audit.success:
        print("audit failed:", audit.error)
        return
    print(audit.final_output)

    gen = await TestGenerationWorkflow().execute(path="src/api/")
    print(gen.final_output)
    for action in gen.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** both `execute` calls are coroutines — `await` them. A
completed run returns `success=True` with the report in
`final_output`; a failure returns `success=False` with a populated
`error` and `error_type`.

### Batch-generate across the lowest-coverage modules

**Goal:** generate tests for many under-covered modules at once.

**Steps:**

```python
import asyncio

from attune.workflows import ParallelTestGenerationWorkflow


async def main() -> None:
    workflow = ParallelTestGenerationWorkflow()
    result = await workflow.execute(top=10, batch_size=5)
    print(result.success)
    print(result.final_output)


asyncio.run(main())
```

**Verify:** `execute` takes `top` (default `200`), `batch_size`
(default `10`), and `output_dir` (default
`tests/behavioral/generated`). It writes generated test files to
`output_dir` and returns their paths in the result. This is also
the workflow behind the `test_gen_parallel` MCP tool.

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

## Comparison

Smart-test and **deep-review** both surface test gaps, but only
smart-test generates the tests to close them.

| | `smart-test` | `deep-review` |
|---|---|---|
| **Scope** | Dedicated to test coverage: audit gaps, then generate tests | One pass of a broader review (security / quality / test gaps) |
| **Test-gap detection** | `test-audit` — three subagents focused on coverage | The `test-gap-reviewer` pass (one of three) |
| **Generates tests** | Yes — `test-gen` and the batch generator | No — it reports gaps, it does not write tests |
| **Slugs** | `attune workflow run test-audit` / `test-gen` | `attune workflow run deep-review` |

Reach for **smart-test** when the goal is coverage — find what's
untested and write tests for it. Reach for **deep-review** when you
want test gaps as one input alongside a security and quality read,
without generating anything. A common flow is deep-review (or
test-audit) to find the gaps, then test-gen to fill them. To repair
*failing* tests rather than write missing ones, see **fix-test**.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `DeprecationWarning: ...execute(src_path=...) is deprecated` | The audit was called with the legacy `src_path` kwarg | Use `path=` instead (the audit still runs) | low |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry | medium |
| Generated tests don't pass as-is | Generation is a predictive starting point | Review, adjust, and run them before committing | medium |
| Audit finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is a
  coroutine on every smart-test workflow. Forgetting to `await` it
  is the single most common mistake.
- **Two slugs, one feature.** The skill / topic is `smart-test`,
  but the CLI slugs are `test-audit` and `test-gen`. And a
  same-named repo-level skill (`.claude/skills/smart-test`) does
  something different — it runs your diff's affected tests.
- **Generation is a draft.** `test-gen` writes a starting point.
  Run and review the output; a generated test that imports the
  wrong symbol or asserts the wrong value is on you to catch.

### Diagnosis order

1. Confirm you are awaiting: `result = await
   TestAuditWorkflow().execute(path="src/")` inside an `async def`
   or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For a CLI "unknown workflow" error, confirm the slug is
   `test-audit` or `test-gen` (not `smart-test`).
4. On an SDK error, inspect `result.metadata` for the captured SDK
   error fields.
5. Confirm the scope: `result.metadata` echoes the run's `path` /
   `src_path`, `depth`, and `max_turns`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and the
> help-docs-single-source spec's decisions.md D6). This section is
> **not** projected verbatim as the FAQ; it contributes the
> feature's author-curated seed questions.

- **Q:** Does smart-test find gaps or write tests?
  **A:** Both — `test-audit` finds and ranks coverage gaps;
  `test-gen` writes pytest tests to close them. The `/smart-test`
  skill can do either or both in sequence.
- **Q:** Why does `attune workflow run smart-test` fail?
  **A:** `smart-test` is the skill / topic name, not a workflow
  slug. Run `attune workflow run test-audit` or
  `attune workflow run test-gen`.
- **Q:** How do I generate tests for many modules at once?
  **A:** Use `ParallelTestGenerationWorkflow().execute(top=N,
  batch_size=M)` (the `test_gen_parallel` MCP tool), which writes
  to `tests/behavioral/generated` by default.
- **Q:** Which calls are async?
  **A:** Every smart-test workflow's `execute` is a coroutine —
  `await` it or use `asyncio.run`.
- **Q:** Can I trust the generated tests?
  **A:** Treat them as a reviewed starting point. Generation is
  predictive — run the tests and check the assertions before
  committing.

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
