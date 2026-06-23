# Doc Gen

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

<!-- attune-generated: source_hash=bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384 feature=doc-gen kind=architecture generated_at=2026-06-23 -->
