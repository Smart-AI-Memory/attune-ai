---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: task
---

# Generate new documentation from source code with three specialized subagents

## Tasks

### Generate docs from the CLI

**Goal:** generate documentation for a module without writing any
Python.

**Steps:**

```bash
# Default depth (standard) over a module:
attune workflow run doc-gen --path src/attune/config.py

# Deep generation, JSON output:
attune workflow run doc-gen --path src/attune/ --depth deep --json
```

**Verify:** the slug is `doc-gen`. `--path` / `-p` defaults to the
current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use
`attune workflow info doc-gen` to confirm registration. The
generated documentation is printed in the result — place it where
it belongs.

### Generate docs from Python

**Goal:** drive doc-gen from a hook or a docs pipeline and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import DocumentGenerationWorkflow


async def main() -> None:
    workflow = DocumentGenerationWorkflow()
    result = await workflow.execute(path="src/attune/api/", depth="deep")

    if not result.success:
        print("generation failed:", result.error)
        return

    print(result.final_output)     # the generated document
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the document in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope the run to keep it fast

**Goal:** generate docs for one module cheaply.

**Steps:**

```python
import asyncio

from attune.workflows import DocumentGenerationWorkflow


async def main() -> None:
    workflow = DocumentGenerationWorkflow()
    result = await workflow.execute(path="src/attune/config.py", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** doc-gen has no `focus` parameter, so the levers are
`path` (point it at a narrower file or directory) and `depth`
(`quick` uses the smallest agent-turn budget). All three passes run
over whatever `path` covers.
