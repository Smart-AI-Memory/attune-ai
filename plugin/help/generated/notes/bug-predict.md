---
name: bug-predict
source: content/features/bug-predict.md
tags:
- bugs
- prediction
- scanning
- race-condition
type: note
---

# Predict likely bug hotspots with three Agent SDK subagents

## Overview

Bug-predict scans a codebase and predicts where bugs are most
likely to hide. It is **SDK-native**: `BugPredictionWorkflow`
delegates the analysis to three specialized Claude Agent SDK
subagents and synthesizes their findings into a single report
with an overall risk score, per-finding file/line locations, and
prioritized prevention advice.

It **predicts** — it does not prove. The three subagents apply
LLM judgment over the code (via Read / Glob / Grep), so findings
are risk hypotheses to triage, not the deterministic output of a
linter. Treat a HIGH finding as "look here first," not "this line
is definitely broken."

You reach bug-predict four ways, all of which run the same
workflow:

- the **`/bug-predict`** skill, inside a Claude Code conversation;
- the CLI — **`attune workflow run bug-predict`**;
- the **`bug_predict`** MCP tool (one required `path` argument);
- the Python API — `await BugPredictionWorkflow().execute(...)`,
  documented here for wiring bug-predict into a hook, a CI step,
  or a custom tool.

A separate set of regex/string pattern helpers also lives in the
module (`bug_predict_patterns.py`). They are an internal,
lower-level utility layer — **not** what the live workflow runs.
The "Notes & tips" and "Design & extension" sections below say
exactly what they do and do not affect.

## Concepts

### Three subagents, one synthesized report

`BugPredictionWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define three subagents,
each scoped to `Read` / `Glob` / `Grep`:

| Subagent | What it looks for |
|----------|-------------------|
| `pattern-scanner` | Null references, type mismatches, race conditions, `eval`/`exec` usage, broad exception handlers, resource leaks, off-by-one errors. Reports file path, line number, pattern type, and severity. |
| `risk-correlator` | Correlates the scanner's findings with file complexity, change frequency, and historical bug density; assigns a per-file risk score and names the highest-risk modules. |
| `prevention-advisor` | Reviews the correlated risks, ranks them by impact, and proposes specific fixes: refactoring, added tests, type annotations, error-handling, and architectural changes. |

The orchestrator then synthesizes all three into one report with
three sections — **Summary** (an overall 0–100 risk score plus a
2–3 sentence executive summary), **Bugs** (grouped HIGH /
MEDIUM / LOW, each with file, line, pattern, and description), and
**Suggestions** (prioritized prevention strategies).

### Depth controls the agent-turn budget

`execute` takes a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`. Depth maps to the maximum number of agent turns the
SDK query may take, and to a per-run cost cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20
turns). Deeper scans let the subagents read more files and reason
longer, at higher cost — the run is bounded by a `max_budget_usd`
derived from the depth.

### `execute` is async, and honors only `path` and `depth`

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
bug-predict mistake.

It reads exactly two keyword arguments from `**kwargs`: `path`
(required) and `depth` (default `"standard"`). Any other keyword
is silently ignored — there is no `file_types`, `exclude`, or
`depth=...` shorthand beyond those two. An empty or missing
`path` returns a failed `WorkflowResult` rather than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from
`attune.workflows`). The synthesized report lands in
`final_output` — a serialized `WorkflowReport` when the findings
parse into categories, or the raw markdown text otherwise — with
a short `summary`, a `suggestions` list, the `cost_report`, the
`provider`, and a `metadata` dict echoing back `path`, `depth`,
and `max_turns`. On failure, `success` is `False` and `error` /
`error_type` carry the reason.

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `BugPredictionWorkflow` (its constructor and async
  `execute`) plus the `WorkflowResult` it returns. Names with a
  leading underscore — the pattern helpers in
  `bug_predict_patterns.py` and `_run_agent_predict` — are
  internal and may change.
- **`format_bug_predict_report` and `main` were removed.** They
  consumed the pre-v4.2.0 dict pipeline shape
  (`overall_risk_score`, `patterns_found`, …), not the
  `WorkflowResult` that `execute` returns, and had no live caller
  once the SDK-native rewrite shipped. Read `result.final_output`
  (a `WorkflowReport` when subagent findings parsed as structured
  output, rendered via `attune.voice.report_renderer.render()`)
  and `result.summary` directly instead.
- **Start shallow, then deepen.** Run `quick` to triage, and only
  spend a `deep` budget on the modules that came back hot.
- **Use `--cheap` for routine CLI runs.** It forces unpinned
  subagents onto Haiku, trading some depth for cost.
