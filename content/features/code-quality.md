---
feature: code-quality
summary: Multi-subagent code review across security, quality, performance, and architecture
tags: [review, quality, security, performance, architecture]
source_globs:
  - src/attune/workflows/code_review.py
nav:
  help: code-quality
  mkdocs:
    how-to: how-to/code-quality
    architecture: architecture/code-quality
    reference: reference/code-quality
---

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

## Quickstart

Review a directory and print the consolidated report.
`CodeReviewWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed review
    print(result.summary)          # short health summary
    print(result.final_output)     # the full consolidated report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest review.

## Tasks

### Review a path from the CLI

**Goal:** run a one-off review over a directory without writing any
Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run code-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run code-review --path src/ --depth deep --json
```

**Verify:** the slug is `code-review` (not `code-quality`).
`--path` / `-p` defaults to the current directory; `--depth`
accepts `quick`, `standard`, or `deep`; `--json` / `-j` emits
machine-readable output. Use `attune workflow info code-review` to
confirm registration and `attune workflow list` to see it alongside
the other workflows.

### Call the review from Python

**Goal:** drive code-quality from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path="src/api/", depth="deep")

    if not result.success:
        print("review failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
review returns `success=True` with the report in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope a review to a smaller area

**Goal:** keep a run fast and cheap by narrowing what it reads.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()

    # A single subsystem, quick pass:
    result = await workflow.execute(path="src/auth/", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** code-quality has no `focus` parameter, so the only
levers are `path` (point it at a narrower directory or file) and
`depth` (`quick` trims the agent-turn budget to 10). All four passes
still run over whatever `path` covers.

## Reference

Code-quality's public surface is the `CodeReviewWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `CodeReviewWorkflow` — `attune.workflows.code_review`

| Symbol | Purpose |
|--------|---------|
| `CodeReviewWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `CodeReviewWorkflow.execute(**kwargs)` | **Async.** Run the review. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `CodeReviewWorkflow.name` | The registered slug, `"code-review"`. |
| `CodeReviewWorkflow.stages` | `["agent-review"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest review of a large or critical area. |

### The four passes

| Subagent | Domain |
|----------|--------|
| `security-reviewer` | eval/exec, injection, path traversal, secrets, auth. |
| `quality-reviewer` | Complexity, error handling, naming, duplication, test-coverage gaps. |
| `perf-reviewer` | N+1, unnecessary copies, blocking I/O in async, missing caching. |
| `architect-reviewer` | Coupling, SOLID, circular deps, API design, abstraction mismatches. |

### `WorkflowResult` fields read after a review

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the review completed. |
| `final_output` | `Any` | The consolidated report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short health summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, and `subagent_transcripts`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/code-quality` in a Claude Code conversation — routes by depth to `code_review` (quick), `code_review` + `bug_predict` (thorough), or `deep_review` (deep). |
| CLI | `attune workflow run code-review --path <p> [--depth quick\|standard\|deep] [--json]`. |
| MCP tool | `code_review` — one required `path` argument; runs at standard depth (the handler does not pass `depth`) and validates the path against the workspace root. |
| Python | `await CodeReviewWorkflow().execute(path=<p>, depth=<d>)`. |

## Comparison

Code-quality (`code-review`) and **deep-review** are both
SDK-native review workflows reached with `attune workflow run
<slug>`, both async, both predictive (LLM judgment) — but they
trade a different mix of passes and one has a narrowing knob.

| | `code-quality` (`code-review`) | `deep-review` |
|---|---|---|
| **Passes** | Four: security, quality, performance, architecture | Three: security, quality, test gaps |
| **Subagents** | `security-` / `quality-` / `perf-` / `architect-reviewer` | `security-` / `quality-` / `test-gap-reviewer` |
| **Narrowing** | None — scope via `path` only | `focus` selects a subset of passes |
| **Turn budget** | 10 / 20 / 40 (quick / standard / deep) | 15 / 30 / 50 |
| **Report sections** | Summary / Security / Quality / Performance / Architecture / Suggestions | Summary / Security / Quality / Test Gaps / Suggestions |
| **Slug** | `attune workflow run code-review` | `attune workflow run deep-review` |

Reach for **code-quality** for the everyday maintainability read —
the performance and architecture passes catch coupling and
inefficiency that a test-focused review skips. Reach for
**deep-review** when test coverage is the concern, or when you want
to narrow to a single domain with `focus`. The `/code-quality`
skill's "deep" option runs deep-review for exactly this reason.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'CodeReviewWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `attune workflow run code-quality` errors "unknown workflow" | The slug is `code-review`, not `code-quality` | Run `attune workflow run code-review` (the skill / help topic is `code-quality`) | medium |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Review stops early / partial report | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **The slug differs from the name.** The feature, skill, and help
  topic are `code-quality`; the workflow slug and MCP tool are
  `code-review`. Use `code-review` for `attune workflow run` and
  the MCP call.
- **Findings are predictions, not proofs.** A CRITICAL or HIGH
  finding means "look here first," not a confirmed defect — and a
  clean review is not a guarantee. Verify before acting.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For an "unknown workflow" CLI error, confirm you used the
   `code-review` slug.
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

- **Q:** What is code quality review?
  **A:** A one-call code review: the `CodeReviewWorkflow` delegates
  to four specialized SDK subagents — security, quality, performance,
  architecture — and synthesizes their findings into a single report
  with an overall 0–100 health score, per-domain findings, and a
  prioritized list of next steps.
- **Q:** When should I run a code quality review?
  **A:** Before opening pull requests, after large refactors, when
  inheriting unfamiliar code, or any time you want a health read on a
  codebase. It is the everyday breadth review.
- **Q:** How do I start a review?
  **A:** Four ways: the `/code-quality` skill in a Claude Code
  conversation, the CLI (`attune workflow run code-review --path
  src/` — note the slug), the `code_review` MCP tool, or the Python
  API (`await CodeReviewWorkflow().execute(path="src/")`).
- **Q:** What's the difference between quick, standard, and deep
  reviews?
  **A:** `depth` sets the agent-turn budget — `quick` 10, `standard`
  20 (the default), `deep` 40. All four passes run at every depth;
  a bigger budget means more thorough passes, not different ones.
  (One nuance: the `/code-quality` *skill* routes a "deep" request
  to the separate deep-review workflow.)
- **Q:** What do the health scores mean?
  **A:** The Summary section opens with an overall 0–100 health
  score synthesized from the four passes — higher is healthier. It
  is an LLM judgment, not a measurement: treat it as a trend signal
  and read the per-domain findings for the substance.
- **Q:** Can I fix issues automatically?
  **A:** The workflow reports; it never modifies files. In a Claude
  Code session, ask the agent to apply specific fixes from the
  report — mechanical ones (unused imports, style) are quick wins;
  structural findings need manual judgment.
- **Q:** How do I focus on specific types of issues?
  **A:** There's no `focus` parameter — all four passes always run.
  Narrow the `path`, use deep-review (which has `focus`), or drill
  into the returned report conversationally ("just show me the
  security findings").
- **Q:** What if I want to compare different parts of my code?
  **A:** Run the workflow once per path (e.g. `src/auth/` then
  `src/api/`) and compare the health scores and finding counts —
  the report is per-run, one path at a time.
- **Q:** Where can I learn more?
  **A:** Say "tell me more" (the coach skill goes progressively
  deeper: concept → procedural → reference), or open this feature's
  quickstart and task guides.
- **Q:** Why does `attune workflow run code-quality` say "unknown
  workflow"?
  **A:** The registered slug is `code-review`. The `code-quality`
  name is the skill / help topic; run the workflow as
  `attune workflow run code-review`.
- **Q:** What's the difference between code-quality and
  deep-review?
  **A:** Code-quality runs four passes — security, quality,
  performance, architecture — and has no narrowing knob.
  Deep-review swaps performance and architecture for a test-gap
  pass and lets you narrow with `focus`. Use code-quality for the
  everyday maintainability read, deep-review when test coverage is
  the concern.
- **Q:** How do I run only the security pass?
  **A:** You can't — code-quality has no `focus`. Either narrow the
  `path`, or use deep-review with `focus=["security"]`.
- **Q:** Which calls are async?
  **A:** `execute` is the only public method and it is a coroutine
  — `await` it or use `asyncio.run`.
- **Q:** Does a clean review mean the code is good?
  **A:** No. Findings are LLM predictions, not proofs, and a clean
  pass is not a guarantee — treat the review as one input.

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

## Design & extension

### Design decisions

- **SDK-native, four review passes.** Code-quality is a single
  `claude_agent_sdk.query` with four subagents — `security-`,
  `quality-`, `perf-`, and `architect-reviewer` — each writing
  under its own report heading. Splitting the passes keeps each
  subagent's context focused; the orchestrator merges them into one
  consolidated report.
- **Breadth without a narrowing knob.** Where deep-review lets
  `focus` trim its passes, code-quality always runs all four — it
  is the default everyday review, and the `/code-quality` skill
  escalates to deep-review (with its `focus`) when you ask for a
  deep pass.
- **Prediction, not certification, is the contract.** The workflow
  returns LLM-judged findings; it trades a linter's precision for
  breadth and a prioritized next-step list. Findings are leads to
  verify, never a guarantee.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI, MCP, and
  Python surfaces all render that same result.

### Extension points

- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost.
- **Scope the run:** point `path` at a narrower directory or file.
- **Add a review pass:** the subagent definitions are built inline
  in `_run_agent_review`, with the names listed in
  `_SUBAGENT_NAMES`; a new pass is a new `AgentDefinition` plus a
  synthesis section in the task template in `code_review.py`.
