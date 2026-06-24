---
name: smart-test
source: content/features/smart-test.md
tags:
- tests
- coverage
- generation
type: task
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

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
