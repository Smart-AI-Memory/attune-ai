---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: note
---

# Generate new documentation from source code with three specialized subagents

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
