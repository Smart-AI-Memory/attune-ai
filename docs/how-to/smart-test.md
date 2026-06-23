# Smart Test

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

<!-- attune-generated: source_hash=d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe feature=smart-test kind=how-to generated_at=2026-06-23 -->
