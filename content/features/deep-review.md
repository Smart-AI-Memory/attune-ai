---
feature: deep-review
summary: Multi-pass code review across security, quality, and test gaps
tags: [review, security, quality, tests]
source_globs:
  - src/attune/workflows/deep_review.py
nav:
  help: deep-review
  mkdocs:
    how-to: how-to/deep-review
    architecture: architecture/deep-review
    reference: reference/deep-review
---

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

## Quickstart

Review a directory and print the consolidated report.
`DeepReviewAgentSDKWorkflow.execute` is an async coroutine, so
drive it with `asyncio.run` (or `await` it inside an existing
event loop):

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
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

**Goal:** run a one-off review over a directory without writing
any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run deep-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run deep-review --path src/ --depth deep --json

# Narrow to the security pass via JSON input:
attune workflow run deep-review --path src/ --input '{"focus": ["security"]}'
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output. There is no dedicated `--focus`
flag — pass `focus` through `--input` as JSON. Use
`attune workflow info deep-review` to confirm registration and
`attune workflow list` to see it alongside the other workflows.

### Call the review from Python

**Goal:** drive deep-review from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
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
review returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, `max_turns`,
and active `focus`.

### Run only the passes you need

**Goal:** scope the review to one or two domains instead of all
three.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()

    # Security pass only:
    sec = await workflow.execute(path="src/auth/", focus=["security"])
    print(sec.final_output)

    # Security + quality, skip test gaps:
    both = await workflow.execute(
        path="src/auth/", focus=["security", "quality"]
    )
    print(both.final_output)


asyncio.run(main())
```

**Verify:** `focus` accepts any subset of `"security"`,
`"quality"`, `"test-gaps"`. Only the named passes run, and
`metadata["focus"]` reflects the active set. An all-invalid
`focus` returns `success=False` with an "Invalid focus values"
error naming the valid options.

## Reference

Deep-review's public surface is the `DeepReviewAgentSDKWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `DeepReviewAgentSDKWorkflow` — `attune.workflows.deep_review`

| Symbol | Purpose |
|--------|---------|
| `DeepReviewAgentSDKWorkflow()` | Construct the workflow. Takes no special constructor arguments (no `system_prompt_suffix`). |
| `DeepReviewAgentSDKWorkflow.execute(**kwargs)` | **Async.** Run the review. Honors `path` (str, required), `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`), and `focus` (list of `"security"` / `"quality"` / `"test-gaps"`, default all three). Returns a `WorkflowResult`. |
| `DeepReviewAgentSDKWorkflow.name` | The registered slug, `"deep-review"`. |
| `DeepReviewAgentSDKWorkflow.stages` | `["deep-review"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 15 | A fast pass on a small path. |
| `standard` | 30 | The default — balanced coverage and cost. |
| `deep` | 50 | The fullest review of a large or critical area. |

### The three passes

| `focus` value | Subagent | Domain |
|---------------|----------|--------|
| `security` | `security-reviewer` | Injection, secrets, path traversal, auth, OWASP Top 10. |
| `quality` | `quality-reviewer` | Complexity, broad excepts, dead code, naming, duplication, type hints, docstrings, long functions. |
| `test-gaps` | `test-gap-reviewer` | Untested paths, missing edge cases, weak assertions, mocks hiding bugs. |

### `WorkflowResult` fields read after a review

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the review completed. |
| `final_output` | `Any` | The consolidated report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short health summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, `focus`, and `workflow`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/deep-review` in a Claude Code conversation. |
| CLI | `attune workflow run deep-review --path <p> [--depth quick\|standard\|deep] [--json] [--input '{"focus": [...]}']`. |
| MCP tool | `deep_review` — one required `path` argument; runs all three passes at standard depth (the handler does not pass `depth` or `focus`). |
| Python | `await DeepReviewAgentSDKWorkflow().execute(path=<p>, depth=<d>, focus=[...])`. |

## Comparison

Deep-review and **security-audit** are both SDK-native review
workflows reached with `attune workflow run <name>`, both
predictive (LLM judgment), but they trade breadth against depth.

| | `deep-review` | `security-audit` |
|---|---|---|
| **Scope** | Three domains in one pass: security, quality, test gaps | Security only |
| **Subagents** | Three: security / quality / test-gap reviewers | Four: vuln-scanner, secret-detector, auth-reviewer, remediation-planner |
| **Narrowing** | `focus` selects a subset of passes | Always the full security sweep |
| **Turn budget** | 15 / 30 / 50 (quick / standard / deep) | 10 / 20 / 40 |
| **Report sections** | Summary / Security / Quality / Test Gaps / Suggestions | Summary / Security / Suggestions |
| **Slug** | `attune workflow run deep-review` | `attune workflow run security-audit` |

Reach for **deep-review** when you want one consolidated
pre-merge read across correctness, maintainability, and test
coverage; reach for **security-audit** when the concern is
specifically the vulnerability surface and you want the deeper,
four-subagent security treatment. Run deep-review with
`focus=["security"]` for a quick security-only pass, or
security-audit for the thorough one.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'DeepReviewAgentSDKWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Invalid focus values. Valid: ..."` | `focus` contained only unrecognized values | Use a subset of `"security"`, `"quality"`, `"test-gaps"` (note the hyphen in `test-gaps`) | medium |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Review stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower path, narrow with `focus`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **`focus` spelling matters.** The valid values are `"security"`,
  `"quality"`, and `"test-gaps"` — `"test-gap"` (no `s`) is
  silently dropped, and an all-invalid `focus` fails the run.
- **Findings are predictions, not proofs.** A CRITICAL or HIGH
  finding means "look here first," not a confirmed defect — and a
  clean review is not a guarantee. Verify before acting.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For a focus error, confirm the values are a subset of
   `security` / `quality` / `test-gaps`.
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, `max_turns`, and active `focus`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and the
> help-docs-single-source spec's decisions.md D6). This section is
> **not** projected verbatim as the FAQ; it contributes the
> feature's author-curated seed questions.

- **Q:** What's the difference between deep-review and
  security-audit?
  **A:** Deep-review covers three domains (security, quality, test
  gaps) in one pass and can be narrowed with `focus`;
  security-audit is security-only with four specialized subagents
  and a deeper treatment. Use deep-review for breadth,
  security-audit for the thorough security sweep.
- **Q:** How do I run only the security pass?
  **A:** `await workflow.execute(path=..., focus=["security"])`,
  or on the CLI `--input '{"focus": ["security"]}'`.
- **Q:** Which calls are async?
  **A:** `execute` is the only public method and it is a
  coroutine — `await` it or use `asyncio.run`.
- **Q:** Is there an `attune deep-review` command?
  **A:** No dedicated subcommand — run it as
  `attune workflow run deep-review`, the `/deep-review` skill, or
  the `deep_review` MCP tool.
- **Q:** Does a clean review mean the code is good?
  **A:** No. Findings are LLM predictions, not proofs, and a clean
  pass is not a guarantee — treat the review as one input.

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `DeepReviewAgentSDKWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_deep_review`, `_SUBAGENT_DEFS` — are internal and may
  change.
- **Use `focus` to keep runs cheap.** A `focus=["security"]` pass
  is faster and cheaper than the full three-domain review; reserve
  the full `deep` run for pre-merge or release gates.
- **Read `metadata["focus"]` to confirm scope.** It records which
  passes actually ran, which is handy when a caller built the
  focus list dynamically.
- **Start shallow, then deepen.** Run `standard` broadly and spend
  a `deep` run only on the modules that came back risky.

## Design & extension

### Design decisions

- **SDK-native, three review passes.** Deep-review is a single
  `claude_agent_sdk.query` with three subagents — a
  `security-reviewer`, a `quality-reviewer`, and a
  `test-gap-reviewer` — each writing under its own report heading.
  Splitting the passes keeps each subagent's context focused; the
  orchestrator merges them into one consolidated report.
- **Breadth with an opt-in narrowing.** Where security-audit goes
  deep on one domain, deep-review covers three by default and lets
  `focus` trim the set — so one workflow serves both the broad
  pre-merge read and a targeted single-domain pass.
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
- **Scope the run:** pass `focus` to run a subset of the three
  passes.
- **Add a review pass:** the subagent definitions live in a
  module-level `_SUBAGENT_DEFS` map and the names in
  `_SUBAGENT_NAMES`; a new pass is a new entry plus a synthesis
  section in the task template in `deep_review.py`.
