---
type: note
name: code-quality-note
feature: code-quality
depth: note
generated_at: 2026-07-14T15:58:49.270997+00:00
source_hash: 1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679
status: generated
---

# Multi-subagent code review across security, quality, performance, and architecture

## Overview

Code-quality runs a code review in one call. It is **SDK-native**:
the `CodeReviewWorkflow` (registered under the slug `code-review`)
delegates to four specialized Claude Agent SDK subagents — one each
for security, quality, performance, and architecture — and
synthesizes their findings into a single report with an overall
health score, per-domain findings, and a prioritized list of next
steps.

It is the **everyday breadth** review: where deep-review trades the
performance and architecture passes for a dedicated test-gap pass
(and lets you narrow with `focus`), code-quality always runs its
four passes and has no narrowing knob. Like the other analysis
workflows it **predicts** rather than proves — the subagents apply
LLM judgment over the code (via Read / Glob / Grep), so a finding is
a lead to verify, not a confirmed defect.

You reach code-quality four ways:

- the **`/code-quality`** skill, inside a Claude Code conversation —
  a router that picks the right tool for the depth you ask for (see
  *The `/code-quality` skill routes by depth* below);
- the CLI — **`attune workflow run code-review`** (note the slug is
  `code-review`, not `code-quality`);
- the **`code_review`** MCP tool (one required `path` argument);
- the Python API — `await CodeReviewWorkflow().execute(...)`,
  documented here for wiring a review into a hook, a pre-merge gate,
  or a custom tool.

A naming note worth pinning up front: the **feature, skill, and
help topic** are all `code-quality`, but the **workflow slug and
MCP tool** are `code-review`. The skill name is the user-facing
front door; the slug is the registered workflow it (sometimes) runs.

## Concepts

### Four review passes, one consolidated report

`CodeReviewWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define four subagents, each
scoped to `Read` / `Glob` / `Grep`:

| Subagent | Pass | What it looks for |
|----------|------|-------------------|
| `security-reviewer` | Security | `eval`/`exec` usage, injection vulnerabilities, path traversal, hardcoded secrets, authentication issues. Reports file, line, severity, and remediation. |
| `quality-reviewer` | Quality | Code complexity, error-handling patterns, naming conventions, duplication, and test-coverage gaps. Reports file, severity, and improvement advice. |
| `perf-reviewer` | Performance | N+1 patterns, unnecessary list copies, blocking I/O in async code, and missing caching opportunities. Reports file, estimated impact, and fix. |
| `architect-reviewer` | Architecture | Coupling between modules, SOLID violations, circular dependencies, API-design issues, and abstraction-level mismatches. Reports affected modules and refactoring suggestions. |

The orchestrator then synthesizes the passes into one report with
six sections — **Summary** (an overall 0–100 health score plus a
2–3 sentence summary), then **Security**, **Quality**,
**Performance**, and **Architecture** (each reviewer's findings),
and **Suggestions** (actionable next steps ordered by priority).
Per-subagent transcripts are recovered and appended under a
**Subagent findings** heading so each pass's findings survive even
when the orchestrator synthesizes tersely or hits the budget cap.

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

### There is no `focus` knob

Unlike deep-review, code-quality has no `focus` parameter — all
four passes always run. `execute` reads exactly two keyword
arguments: `path` (required) and `depth` (default `"standard"`).
To scope a review, point `path` at a narrower directory or file.

### `execute` is async

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake. An empty or missing `path` returns a failed
`WorkflowResult` ("path argument is required") rather than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`). The
consolidated report lands in `final_output` — a serialized report
when the findings parse, or the raw markdown otherwise — with a
short `summary`, a `suggestions` list, the `cost_report`, the
`provider`, and a `metadata` dict echoing `path`, `depth`,
`max_turns`, and the recovered `subagent_transcripts`. On failure,
`success` is `False` and `error` / `error_type` carry the reason.

### Code-quality can recommend a follow-up bug-predict run

When the synthesized review surfaces security-shaped findings — a
CWE/CVE reference, an injection or path-traversal mention, a
hardcoded-secret call-out, or a literal `eval(` / `exec(` — the
workflow prints an `ATTUNE_REC` marker recommending a `bug-predict`
run on the same scope. code-quality reads and narrates; bug-predict
pinpoints the exact line. The ops dashboard's runner parses the
marker and renders an action card.

### The `/code-quality` skill routes by depth

The `/code-quality` skill is not a thin wrapper over one workflow —
it is a router that picks the tool for the depth you ask for:

- **Quick** → `code_review` alone;
- **Thorough** → `code_review` **and** `bug_predict`, then merges
  and deduplicates the results;
- **Deep** → `deep_review` (the multi-pass security / quality /
  test-gaps review).

So a "deep" code-quality request runs the *deep-review* workflow,
not a deeper code-review. The CLI, MCP, and Python surfaces, by
contrast, drive `CodeReviewWorkflow` directly.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `CodeReviewWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_review`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one subsystem is far faster than a `deep` pass over `src/`;
  reserve the full `deep` run for pre-merge or release gates.
- **Watch for the bug-predict recommendation.** When the review
  surfaces security-shaped findings, the run emits an `ATTUNE_REC`
  suggesting a `bug-predict` pass on the same scope to locate the
  exact lines.
- **Read `metadata` to confirm scope.** It records the `path`,
  `depth`, and `max_turns` the run actually used.
