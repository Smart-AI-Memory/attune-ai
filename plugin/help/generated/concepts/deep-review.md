---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: concept
---

# Multi-pass code review across security, quality, and test gaps

## Overview

Deep-review runs a multi-pass code review in one call. It is
**SDK-native**: `DeepReviewAgentSDKWorkflow` delegates to three
specialized Claude Agent SDK subagents — one each for security,
code quality, and test gaps — and synthesizes their findings into
a single consolidated report with an overall health score,
severity-ordered findings per domain, and a prioritized list of
next steps.

It is the **breadth** option among the analysis workflows: where
security-audit goes deep on vulnerabilities alone, deep-review
covers three concerns in one pass and lets you narrow to a subset
with `focus`. Like the others it **predicts** rather than proves —
the subagents apply LLM judgment over the code (via Read / Glob /
Grep), so a finding is a lead to verify, not a confirmed defect.

You reach deep-review four ways, all of which run the same
workflow:

- the **`/deep-review`** skill, inside a Claude Code conversation;
- the CLI — **`attune workflow run deep-review`**;
- the **`deep_review`** MCP tool (one required `path` argument);
- the Python API — `await DeepReviewAgentSDKWorkflow().execute(...)`,
  documented here for wiring a review into a hook, a pre-merge
  gate, or a custom tool.

## Concepts

### Three review passes, one consolidated report

`DeepReviewAgentSDKWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define three subagents,
each scoped to `Read` / `Glob` / `Grep`:

| Subagent | Pass | What it looks for |
|----------|------|-------------------|
| `security-reviewer` | Security | `eval`/`exec` and injection vectors, path traversal, hardcoded secrets, SQL/command injection, unsafe deserialization, auth/authz flaws, OWASP Top 10. Reports under a `## Security` heading. |
| `quality-reviewer` | Quality | Excessive complexity (>10 per function), broad exception handling, dead code and unused imports, poor naming, duplication, missing type hints / docstrings on public APIs, functions over 50 lines. Reports under `## Quality`. |
| `test-gap-reviewer` | Test gaps | Public functions with no coverage, untested error paths, missing edge cases (empty / None / boundaries), missing integration tests, mocks that hide bugs, weak assertions. Reports under `## Test Gaps`. |

The orchestrator then synthesizes the passes into one report with
five sections — **Summary** (an overall 0–100 health score plus a
2–3 sentence summary and finding counts by severity), then
**Security**, **Quality**, and **Test Gaps** (each domain's
findings, ordered by severity / priority), and **Suggestions**
(the top 5–10 next steps, each referencing the finding it
addresses).

### `focus` narrows the review to a subset of passes

By default all three passes run. Pass `focus` — a list of any of
`"security"`, `"quality"`, `"test-gaps"` — to run only those
passes:

- `focus=["security"]` runs the security pass alone;
- `focus=["security", "quality"]` skips the test-gap pass;
- an empty or all-invalid `focus` returns a failed
  `WorkflowResult` ("Invalid focus values").

This is deep-review's own knob — it has no `system_prompt_suffix`
(unlike bug-predict / security-audit). Note the spelling:
`"test-gaps"` (hyphen), not `"test-gap"`.

### Depth controls the agent-turn budget

`execute` takes a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`. Depth maps to the maximum agent turns and a per-run
cost cap. Deep-review's budgets are higher than the single-domain
workflows', since it covers three passes:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 15 |
| `standard` | 30 |
| `deep` | 50 |

An unrecognized depth falls back to the standard budget (30
turns).

### `execute` is async

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake. It reads three keyword arguments: `path` (required),
`depth` (default `"standard"`), and `focus` (optional). An empty
or missing `path` returns a failed `WorkflowResult` rather than
raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`).
The consolidated report lands in `final_output` — a serialized
report when the findings parse, or the raw markdown otherwise —
with a short `summary`, a `suggestions` list, the `cost_report`,
the `provider`, and a `metadata` dict echoing `path`, `depth`,
`max_turns`, the active `focus`, and `workflow`. On failure,
`success` is `False` and `error` / `error_type` carry the reason.
