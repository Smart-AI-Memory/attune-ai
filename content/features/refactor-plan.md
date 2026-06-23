---
feature: refactor-plan
summary: Prioritize tech debt — scan for code smells and generate a refactoring roadmap
tags: [refactor, tech-debt, complexity]
source_globs:
  - src/attune/workflows/refactor_plan.py
  - src/attune/workflows/refactor_plan_report.py
nav:
  help: refactor-plan
  mkdocs:
    how-to: how-to/refactor-plan
    architecture: architecture/refactor-plan
    reference: reference/refactor-plan
---

## Overview

Refactor-plan turns "this code needs work" into a prioritized
roadmap. It is **SDK-native**: `RefactorPlanWorkflow` delegates to
three specialized Claude Agent SDK subagents — one scans for tech
debt, one assesses the impact of changing it, and one assembles a
prioritized plan — and synthesizes their findings into a single
report with an overall tech-debt score, a ranked list of
refactoring opportunities (each with an effort estimate and risk
level), and an ordered set of next steps.

It **plans, it doesn't change code**: the subagents are scoped to
`Read` / `Glob` / `Grep`, so refactor-plan reads the codebase and
produces a roadmap — it is the *decide what to do* half of
refactoring, paired with **simplify-code** for the *do it* half
(see *Plan versus act* below). Like the other analysis workflows
it **predicts** rather than proves — its findings are LLM judgments
to verify, not a mechanical debt report.

You reach refactor-plan four ways:

- the **`/refactor`** skill, inside a Claude Code conversation —
  routes a full analysis to refactor-plan, or a complexity-only
  pass to simplify-code;
- the CLI — **`attune workflow run refactor-plan`**;
- the **`refactor_plan`** MCP tool (an optional `path`, defaulting
  to the current directory);
- the Python API — `await RefactorPlanWorkflow().execute(...)`,
  documented here for wiring planning into a hook or report.

## Concepts

### Three passes, one prioritized roadmap

`RefactorPlanWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define three subagents, each
scoped to `Read` / `Glob` / `Grep`:

| Subagent | Pass | What it does |
|----------|------|--------------|
| `debt-scanner` | Find the debt | Scans for code smells, duplication, complex conditionals, dead code, overly long functions, and deeply nested logic. Reports file, line, severity, and a brief description. |
| `impact-analyzer` | Weigh the risk | Assesses test coverage of affected code, dependency chains, API-surface changes, and downstream consumers — the cost of touching each candidate. |
| `plan-generator` | Order the work | Turns the scanner's and analyzer's findings into a prioritized plan: per item an effort estimate (small/medium/large), a risk level (low/medium/high), the expected benefit, and a suggested implementation order. |

The orchestrator then synthesizes the passes into one report with
three sections — **Summary** (an overall 0–100 tech-debt score plus
a 2–3 sentence summary of the opportunities found),
**Refactoring** (the prioritized opportunities with effort
estimates and risk levels), and **Suggestions** (actionable next
steps ordered by priority, including quick wins and longer-term
improvements).

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

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`). The
roadmap lands in `final_output` — a serialized report when the
findings parse, or the raw markdown otherwise — with a short
`summary`, a `suggestions` list, the `cost_report`, the `provider`,
and a `metadata` dict echoing `path`, `depth`, and `max_turns`. On
failure, `success` is `False` and `error` / `error_type` carry the
reason.

### Plan versus act

Refactor-plan and **simplify-code** are the two halves the
`/refactor` skill routes between. Refactor-plan *analyzes* — it
produces a roadmap and changes nothing. Simplify-code *acts* — it
reduces complexity in a target file (flattening nested
conditionals, inlining trivial helpers, removing dead code).
Reach for refactor-plan to decide what to tackle and in what
order; reach for simplify-code to apply a focused cleanup.

## Quickstart

Analyze a directory and print the refactoring roadmap.
`RefactorPlanWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed analysis
    print(result.summary)          # short tech-debt summary
    print(result.final_output)     # the full roadmap


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest roadmap.

## Tasks

### Generate a roadmap from the CLI

**Goal:** produce a prioritized refactoring plan for a directory
without writing any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run refactor-plan --path src/

# Deep analysis, JSON output for a report:
attune workflow run refactor-plan --path src/ --depth deep --json
```

**Verify:** the slug is `refactor-plan`. `--path` / `-p` defaults
to the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use
`attune workflow info refactor-plan` to confirm registration.

### Call the planner from Python

**Goal:** drive refactor-plan from a hook or scheduled report and
act on the result.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/legacy/", depth="deep")

    if not result.success:
        print("analysis failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the roadmap in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope the analysis to a smaller area

**Goal:** keep a run fast and focused on the module you care about.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/attune/config.py", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** refactor-plan has no `focus` parameter, so the levers
are `path` (point it at a narrower directory or file) and `depth`
(`quick` trims the agent-turn budget to 10). All three passes run
over whatever `path` covers.

## Reference

Refactor-plan's public surface is the `RefactorPlanWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `RefactorPlanWorkflow` — `attune.workflows.refactor_plan`

| Symbol | Purpose |
|--------|---------|
| `RefactorPlanWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `RefactorPlanWorkflow.execute(**kwargs)` | **Async.** Run the analysis. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `RefactorPlanWorkflow.name` | The registered slug, `"refactor-plan"`. |
| `RefactorPlanWorkflow.stages` | `["agent-plan"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest roadmap of a large or legacy area. |

### The three passes

| Subagent | Domain |
|----------|--------|
| `debt-scanner` | Code smells, duplication, complex conditionals, dead code, long functions, deep nesting. |
| `impact-analyzer` | Test coverage, dependency chains, API-surface changes, downstream consumers. |
| `plan-generator` | Prioritized plan: effort (small/medium/large), risk (low/medium/high), benefit, order. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the analysis completed. |
| `final_output` | `Any` | The roadmap — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short tech-debt summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/refactor` in a Claude Code conversation — full analysis routes to refactor-plan; a complexity-only pass routes to simplify-code. |
| CLI | `attune workflow run refactor-plan --path <p> [--depth quick\|standard\|deep] [--json]`. |
| MCP tool | `refactor_plan` — optional `path` (defaults to the current directory), validated against the workspace root. |
| Python | `await RefactorPlanWorkflow().execute(path=<p>, depth=<d>)`. |

## Comparison

Refactor-plan and **code-quality** are both SDK-native, predictive,
read-only analysis workflows reached with `attune workflow run
<slug>` — but they answer different questions.

| | `refactor-plan` | `code-quality` |
|---|---|---|
| **Question** | What tech debt should I tackle, and in what order? | Is this code healthy across security, quality, performance, architecture? |
| **Subagents** | Three: `debt-scanner`, `impact-analyzer`, `plan-generator` | Four: `security-`, `quality-`, `perf-`, `architect-reviewer` |
| **Output** | A prioritized roadmap with effort + risk per item | A health report with findings per domain |
| **Sections** | Summary / Refactoring / Suggestions | Summary / Security / Quality / Performance / Architecture / Suggestions |
| **Slug** | `attune workflow run refactor-plan` | `attune workflow run code-review` |

Reach for **refactor-plan** when you've decided to invest in
cleanup and need a sequenced plan; reach for **code-quality** for a
broad health read across more concerns. To actually *apply* a
cleanup once the plan names it, use **simplify-code**.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'RefactorPlanWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Roadmap stops early / partial report | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **It plans, it doesn't apply.** Refactor-plan produces a roadmap;
  it does not edit code. Use simplify-code (or your own change) to
  act on it.
- **Findings are predictions, not proofs.** A high-priority item
  means "look here first," not a confirmed defect. Verify the
  effort and risk estimates against the real code before committing
  to them.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and the
> help-docs-single-source spec's decisions.md D6). This section is
> **not** projected verbatim as the FAQ; it contributes the
> feature's author-curated seed questions.

- **Q:** Does refactor-plan change my code?
  **A:** No. It analyzes and produces a prioritized roadmap; its
  subagents only read the codebase. To apply a cleanup, use
  simplify-code.
- **Q:** What's the difference between refactor-plan and
  code-quality?
  **A:** Refactor-plan ranks tech debt and sequences the work;
  code-quality reports health across security, quality,
  performance, and architecture. Use refactor-plan to plan a
  cleanup, code-quality for a broad review.
- **Q:** How do I make a run cheaper?
  **A:** Narrow the `path` and use a shallower `depth` (`quick`
  uses the smallest agent-turn budget).
- **Q:** Which calls are async?
  **A:** `execute` is the only public method and it is a coroutine
  — `await` it or use `asyncio.run`.
- **Q:** Does a clean roadmap mean there's no debt?
  **A:** No. Findings are LLM predictions, not proofs — treat the
  roadmap as one informed input.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `RefactorPlanWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_plan`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Plan with refactor-plan, act with simplify-code.** Run the
  planner to get a sequenced roadmap, then apply individual items
  with simplify-code or your own edits.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one module is far faster than a `deep` pass over `src/`.
- **Read `metadata` to confirm scope.** It records the `path`,
  `depth`, and `max_turns` the run actually used.

## Design & extension

### Design decisions

- **SDK-native, three planning passes.** Refactor-plan is a single
  `claude_agent_sdk.query` with three subagents — a `debt-scanner`,
  an `impact-analyzer`, and a `plan-generator` — each writing under
  its own heading. Splitting scanning, impact, and planning keeps
  each subagent's context focused; the orchestrator merges them
  into one prioritized roadmap.
- **Plan, don't apply.** The subagents are read-only (`Read` /
  `Glob` / `Grep`), so refactor-plan produces a roadmap and leaves
  the code untouched — applying the plan is simplify-code's job.
- **Prediction, not certification, is the contract.** The workflow
  returns LLM-judged opportunities with effort and risk estimates;
  it trades a metric's precision for a sequenced, actionable plan.
  Findings are leads to verify, never a guarantee.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (roadmap in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI, MCP, and
  Python surfaces all render that same result.

### Extension points

- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost.
- **Scope the run:** point `path` at a narrower directory or file.
- **Add a planning pass:** the subagent definitions are built
  inline in `_run_agent_plan`, with the names listed in
  `_SUBAGENT_NAMES`; a new pass is a new `AgentDefinition` plus a
  synthesis section in the task template in `refactor_plan.py`.
