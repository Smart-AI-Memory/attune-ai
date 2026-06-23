# Doc Gen

## Quickstart

Generate documentation for a directory and print the result.
`DocumentGenerationWorkflow.execute` is an async coroutine, so
drive it with `asyncio.run` (or `await` it inside an existing event
loop):

```python
import asyncio

from attune.workflows import DocumentGenerationWorkflow


async def main() -> None:
    workflow = DocumentGenerationWorkflow()
    result = await workflow.execute(path="src/attune/config.py")

    print(result.success)          # True on a completed run
    print(result.summary)          # short overview
    print(result.final_output)     # the generated documentation


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="...")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest treatment.

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

## Reference

Doc-gen's public surface is the `DocumentGenerationWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `DocumentGenerationWorkflow` — `attune.workflows.document_gen`

| Symbol | Purpose |
|--------|---------|
| `DocumentGenerationWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `DocumentGenerationWorkflow.execute(**kwargs)` | **Async.** Generate docs. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `DocumentGenerationWorkflow.default_context(xml_config=None)` | Classmethod returning a `WorkflowContext` pre-configured with prompt and parsing services, for composition. |
| `DocumentGenerationWorkflow.name` | The registered slug, `"doc-gen"`. |
| `DocumentGenerationWorkflow.stages` | `["agent-gen"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a single module. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest treatment of a large or public-facing area. |

### The three passes

| Subagent | Role |
|----------|------|
| `outline-planner` | Plans the doc structure: modules, APIs, example sections. |
| `content-writer` | Writes the content with code examples and API references. |
| `polish-reviewer` | Refines for clarity and consistency. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | The generated document — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short overview of the documented codebase. |
| `suggestions` | `list[NextAction]` | Recommendations for improving coverage. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/doc-gen` in a Claude Code conversation — routes to `doc_gen` (generate), `doc_audit` (stale/missing), or `doc_orchestrator` (pipeline). |
| CLI | `attune workflow run doc-gen --path <p> [--depth quick\|standard\|deep] [--json]`. |
| Python | `await DocumentGenerationWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384 feature=doc-gen kind=how-to generated_at=2026-06-23 -->
