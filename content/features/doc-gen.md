---
feature: doc-gen
summary: Generate new documentation from source code with three specialized subagents
tags: [docs, documentation, generation]
source_globs:
  - src/attune/workflows/document_gen/**
nav:
  help: doc-gen
  mkdocs:
    how-to: how-to/doc-gen
    architecture: architecture/doc-gen
    reference: reference/doc-gen
---

## Overview

Doc-gen generates new documentation from source code. It is
**SDK-native**: `DocumentGenerationWorkflow` delegates to three
specialized Claude Agent SDK subagents — one plans the outline, one
writes the content, one polishes it — and synthesizes their output
into a single document with a summary, a structure outline, the
written documentation, and suggestions for improving coverage.

It is the **creation** member of the documentation family: where
doc-audit checks for stale or missing docs and doc-orchestrator
runs a full maintenance pipeline, doc-gen writes new content from
the code it reads. Its subagents are scoped to `Read` / `Glob` /
`Grep`, so doc-gen **produces documentation content in its result
for you to review and place** — it reads the source and returns
generated docs; it does not write files to disk.

You reach doc-gen these ways:

- the **`/doc-gen`** skill, inside a Claude Code conversation —
  routes documentation work to `doc_gen` (generate), `doc_audit`
  (find stale/missing docs), or `doc_orchestrator` (the full
  pipeline);
- the CLI — **`attune workflow run doc-gen`**;
- the Python API — `await DocumentGenerationWorkflow().execute(...)`,
  documented here for wiring generation into a hook or a docs
  pipeline.

The reliable programmatic surfaces are the CLI and the Python API
(see *Reaching doc-gen reliably* below).

## Concepts

### Three passes, one document

`DocumentGenerationWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define three subagents, each
scoped to `Read` / `Glob` / `Grep`:

| Subagent | Pass | What it does |
|----------|------|--------------|
| `outline-planner` | Plan | Plans the documentation structure — modules, APIs, and example sections to cover. |
| `content-writer` | Write | Writes the documentation content, with code examples and API references for each section. |
| `polish-reviewer` | Polish | Reviews and refines the written content for clarity and consistency. |

The orchestrator then synthesizes the passes into one document with
four sections — **Summary** (a 2–3 sentence overview of the
documented codebase and its purpose), **Outline** (the structure
from the outline planner), **Documentation** (the full written
content), and **Suggestions** (recommendations for improving
coverage, clarity, or organization).

### Depth controls the agent-turn budget

`execute` takes a `depth` of `"quick"`, `"standard"` (default), or
`"deep"`. Depth maps to the maximum agent turns and a per-run cost
cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20 turns).

### `execute` is async

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake. It reads two keyword arguments: `path` (required) and
`depth` (default `"standard"`). An empty or missing `path` returns
a failed `WorkflowResult` ("path argument is required") rather than
raising.

### It generates content, it doesn't write files

Doc-gen's subagents have only `Read` / `Glob` / `Grep` — no Write.
The generated documentation comes back **in the result**
(`final_output`), not as files written to your tree. Review it and
place it where it belongs.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`). The
document lands in `final_output` — a serialized report when the
findings parse, or the raw markdown otherwise — with a short
`summary`, a `suggestions` list, the `cost_report`, the `provider`,
and a `metadata` dict echoing `path`, `depth`, and `max_turns`. On
failure, `success` is `False` and `error` / `error_type` carry the
reason.

### Reaching doc-gen reliably

Drive doc-gen through the **CLI** (`attune workflow run doc-gen
--path <p>`) or the **Python API**
(`DocumentGenerationWorkflow().execute(path=<p>)`) — both pass the
`path` the workflow expects. The `/doc-gen` skill is the
conversational front door. (If you call the workflow directly,
pass `path` — the documented kwarg — not a source string.)

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

## Comparison

Doc-gen is the **creation** workflow in a family of three
documentation tools the `/doc-gen` skill routes between:

| Tool | Role |
|------|------|
| `doc-gen` (this feature) | Generate new documentation from source code. |
| `doc_audit` | Check for stale or missing documentation. |
| `doc_orchestrator` | Run a full documentation maintenance pipeline. |

Reach for **doc-gen** when you need new content written for a
module that lacks it; reach for **doc_audit** to find what's stale
or missing first; reach for **doc_orchestrator** when you want the
end-to-end maintenance pass. A common flow is doc_audit to find the
gaps, then doc-gen to fill them.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'DocumentGenerationWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` (e.g. passing a source string instead of `path`) | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Generation stops early / partial document | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| Expected files weren't written | Doc-gen returns content in the result; it does not write files | Take the document from `final_output` and place it yourself | low |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the main
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **Pass `path`, not a source string.** `execute` reads `path` (and
  `depth`); it does not take a raw source-code string or a
  `doc_type`. The CLI and Python API supply `path` correctly.
- **It generates, it doesn't place.** The output is documentation
  content in the result, not files on disk — review and position it
  yourself.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. If `error` is "path argument is required", confirm you passed
   `path=` (not a source string or other kwarg).
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`, `depth`,
   and `max_turns`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and the
> help-docs-single-source spec's decisions.md D6). This section is
> **not** projected verbatim as the FAQ; it contributes the
> feature's author-curated seed questions.

- **Q:** Does doc-gen write documentation files for me?
  **A:** No. Its subagents are read-only; the generated
  documentation comes back in `final_output` for you to review and
  place.
- **Q:** What's the difference between doc-gen, doc-audit, and
  doc-orchestrator?
  **A:** Doc-gen creates new docs; doc-audit finds stale or missing
  docs; doc-orchestrator runs the full maintenance pipeline. The
  `/doc-gen` skill routes among them.
- **Q:** How do I run doc-gen reliably from code?
  **A:** Use the CLI (`attune workflow run doc-gen --path <p>`) or
  Python (`DocumentGenerationWorkflow().execute(path=<p>)`) — both
  pass the `path` the workflow expects.
- **Q:** Which calls are async?
  **A:** `execute` is a coroutine — `await` it or use
  `asyncio.run`.
- **Q:** How do I keep a run cheap?
  **A:** Narrow the `path` and use a shallower `depth` (`quick`
  uses the smallest agent-turn budget).

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `DocumentGenerationWorkflow` and its async `execute` (plus the
  `default_context` classmethod for composition), and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_gen`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Audit first, then generate.** Run doc-audit to find the gaps,
  then point doc-gen at the modules that need new content.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one module is far faster than a `deep` pass over `src/`.
- **Take the output from `final_output`.** Doc-gen returns
  generated content; review it and place it where it belongs.

## Design & extension

### Design decisions

- **SDK-native, three generation passes.** Doc-gen is a single
  `claude_agent_sdk.query` with three subagents — an
  `outline-planner`, a `content-writer`, and a `polish-reviewer` —
  each writing under its own heading. Splitting planning, writing,
  and polishing keeps each subagent's context focused; the
  orchestrator merges them into one document.
- **Generate content, don't place it.** The subagents are
  read-only (`Read` / `Glob` / `Grep`), so doc-gen returns the
  documentation in its result rather than writing files — leaving
  placement and review to the caller.
- **Creation, not maintenance.** Doc-gen writes new documentation;
  the audit and orchestrator tools own staleness checking and the
  full maintenance pipeline.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (document in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI and Python
  surfaces render that same result.

### Extension points

- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost.
- **Scope the run:** point `path` at a narrower directory or file.
- **Compose it:** use `default_context()` to drive doc-gen with a
  custom `WorkflowContext` (prompt and parsing services).
- **Add a generation pass:** the subagent definitions are built
  inline in `_run_agent_gen`, with the names listed in
  `_SUBAGENT_NAMES`; a new pass is a new `AgentDefinition` plus a
  synthesis section in the task template in `document_gen/workflow.py`.
