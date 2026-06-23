---
type: concept
name: refactor-plan-concept
feature: refactor-plan
depth: concept
generated_at: 2026-06-23T16:06:40.108874+00:00
source_hash: 198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb
status: generated
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

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
