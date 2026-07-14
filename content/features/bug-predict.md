---
feature: bug-predict
summary: Predict likely bug hotspots with three Agent SDK subagents
tags: [bugs, quality, analysis]
source_globs:
  - src/attune/workflows/bug_predict.py
  - src/attune/workflows/bug_predict_patterns.py
nav:
  help: bug-predict
  mkdocs:
    how-to: how-to/bug-predict
    architecture: architecture/bug-predict
    reference: reference/bug-predict
---

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

## Quickstart

Scan a directory and print the synthesized report.
`BugPredictionWorkflow.execute` is an async coroutine, so drive
it with `asyncio.run` (or `await` it inside an existing event
loop):

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed scan
    print(result.summary)          # short executive summary
    print(result.final_output)     # the full synthesized report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for a
longer, costlier scan.

## Tasks

### Scan a path from the CLI

**Goal:** run a one-off prediction over a directory without
writing any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run bug-predict --path src/

# Deeper scan, JSON output for a CI step:
attune workflow run bug-predict --path src/ --depth deep --json

# Cost-saving pass (unpinned subagents run on Haiku):
attune workflow run bug-predict --path src/ --cheap
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output; `--cheap` forces every subagent
without an explicit model onto Haiku for that run. Use
`attune workflow info bug-predict` to confirm the workflow is
registered, and `attune workflow list` to see it alongside the
other workflows.

### Call the prediction from Python

**Goal:** drive bug-predict from a hook or custom tool and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path="src/api/", depth="quick")

    if not result.success:
        print("scan failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
scan returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns` actually used.

### Steer the scan with a prompt suffix

**Goal:** narrow or focus the analysis without replacing the
built-in orchestrator behavior.

**Steps:**

```python
import asyncio

from attune.workflows import BugPredictionWorkflow


async def main() -> None:
    workflow = BugPredictionWorkflow(
        system_prompt_suffix=(
            "Focus on authentication code. "
            "Skip LOW severity findings."
        ),
    )
    result = await workflow.execute(path="src/auth/")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** `system_prompt_suffix` is a keyword-only constructor
argument appended to the orchestrator's system prompt at call
time. The three subagents still run their normal analysis; the
suffix only steers the orchestrator. The empty-string default
leaves behavior unchanged (this is the hook discovery-sweep's
`BugPredictSource` uses to augment the prompt per instance).

## Reference

Bug-predict's public surface is the `BugPredictionWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `BugPredictionWorkflow` — `attune.workflows.bug_predict`

| Symbol | Purpose |
|--------|---------|
| `BugPredictionWorkflow(*, system_prompt_suffix="", **kwargs)` | Construct the workflow. `system_prompt_suffix` (keyword-only) is appended to the orchestrator's system prompt; the empty default preserves stock behavior. Other kwargs pass to `BaseWorkflow`. |
| `BugPredictionWorkflow.execute(**kwargs)` | **Async.** Run the prediction. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`); other kwargs are ignored. Returns a `WorkflowResult`. |
| `BugPredictionWorkflow.name` | The registered slug, `"bug-predict"`. |
| `BugPredictionWorkflow.stages` | `["agent-predict"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast first pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | A thorough scan of a large or high-risk area. |

### `WorkflowResult` fields read after a scan

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the scan completed. |
| `final_output` | `Any` | The synthesized report — a serialized `WorkflowReport` when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short executive summary of the run. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/bug-predict` in a Claude Code conversation. |
| CLI | `attune workflow run bug-predict --path <p> [--depth quick\|standard\|deep] [--json] [--cheap]`. |
| MCP tool | `bug_predict` — one required `path` argument; runs at standard depth (the handler does not pass `depth`). |
| Python | `await BugPredictionWorkflow().execute(path=<p>, depth=<d>)`. |

## Comparison

Bug-predict and **security-audit** both scan the same codebase
through Agent SDK subagents and are both reached with
`attune workflow run <name>`, but they answer different
questions.

| | `bug-predict` | `security-audit` |
|---|---|---|
| **Question answered** | "Where are bugs most likely to be?" | "Where are the security vulnerabilities?" |
| **Focus** | Correctness-risk hotspots: null refs, type mismatches, race conditions, broad excepts, resource leaks, off-by-one | Security issues: `eval`/`exec`, path traversal, injection, hardcoded secrets |
| **Output** | Overall risk score + bugs by severity + prevention advice | Vulnerability findings by severity |
| **Slug** | `attune workflow run bug-predict` | `attune workflow run security-audit` |
| **Nature** | Predictive (LLM judgment), not a deterministic linter | Predictive (LLM judgment), not a deterministic linter |

Reach for **bug-predict** when you want a broad correctness-risk
triage of a module; reach for **security-audit** when the concern
is specifically a vulnerability surface. They overlap on
`eval`/`exec` (both flag it) and complement each other on a
pre-release sweep.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BugPredictionWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Scan stops early / partial report | The depth's agent-turn or `max_budget_usd` budget was reached | Use a shallower path or raise depth deliberately (cost rises) | medium |
| `ImportError: cannot import name 'format_bug_predict_report'` | The pre-v4.2.0 formatter module was removed (dead code, zero live callers) | Read `result.final_output` / `result.summary` directly, or render via `attune.voice.report_renderer.render()` | medium |
| Editing `./attune.config.yml`'s `bug_predict` block changes nothing | That block configures the internal static pattern helpers, which the live SDK workflow does not run | Steer the scan with `system_prompt_suffix` (or a deeper `depth`) instead | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it
  is the single most common bug-predict mistake.
- **Findings are predictions, not proofs.** The subagents apply
  LLM judgment; a HIGH finding means "investigate first," not
  "this is definitely a bug." Confirm before acting.
- **The static helpers are not the live scanner.** The regex
  detectors in `bug_predict_patterns.py` and the
  `./attune.config.yml` `bug_predict` settings are a separate
  layer; they do not change what the three subagents do.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns` actually used.
5. Run the related tests: `pytest -k bug_predict -v`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and
> the help-docs-single-source spec's decisions.md D6). This
> section is **not** projected verbatim as the FAQ; it
> contributes the feature's author-curated seed questions.

- **Q:** Does bug-predict fix the bugs it finds?
  **A:** No. It predicts and prioritizes likely-bug hotspots and
  suggests prevention strategies; applying fixes is a separate
  step you (or a refactor workflow) take.
- **Q:** Is there an `attune bug-predict` command?
  **A:** No dedicated subcommand — run it as
  `attune workflow run bug-predict`, or use the `/bug-predict`
  skill or the `bug_predict` MCP tool.
- **Q:** Which calls are async?
  **A:** `execute` is the only public method and it is a
  coroutine — `await` it or use `asyncio.run`.
- **Q:** What does `depth` change?
  **A:** The agent-turn budget (quick 10, standard 20, deep 40)
  and the per-run cost cap — deeper scans read more and cost
  more.
- **Q:** Why didn't my `./attune.config.yml` `bug_predict` settings
  change the results?
  **A:** Those settings configure the internal static pattern
  helpers, not the live SDK subagents. Steer the scan with
  `system_prompt_suffix` or a deeper `depth` instead.

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

## Design & extension

### Design decisions

- **SDK-native, three specialized subagents.** Since v4.2.0,
  bug-predict is a single `claude_agent_sdk.query` with three
  subagents — `pattern-scanner` (detection), `risk-correlator`
  (scoring), and `prevention-advisor` (advice). Splitting the
  work keeps each subagent's context focused and lets one be
  changed without touching the others; the cost is an extra
  synthesis step in the orchestrator.
- **Prediction, not deterministic scanning, is the contract.**
  The workflow returns LLM-judged risk hypotheses, deliberately
  trading a linter's precision for breadth and prioritization.
  This is why findings are framed as hotspots to triage.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); callers own
  presentation. The CLI, MCP, and skill surfaces all render that
  same result.

### Extension points

- **Steer a single run:** pass `system_prompt_suffix` to the
  constructor to append instructions to the orchestrator prompt
  without subclassing — the pattern discovery-sweep's
  `BugPredictSource` uses.
- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost; `--cheap` on the CLI
  forces unpinned subagents onto Haiku.
- **The static pattern helpers are a separate layer.**
  `bug_predict_patterns.py` exposes regex/string detectors
  (`_is_dangerous_eval_usage`, `_has_problematic_exception_handlers`,
  …) and `_load_bug_predict_config`, which reads the
  `./attune.config.yml` `bug_predict` block
  (`risk_threshold`, `exclude_files`,
  `acceptable_exception_contexts`). `_should_exclude_file` is
  reused by `workflow_patterns/behavior.py`; the eval/exception
  detectors are not wired into the live SDK workflow. Treat them
  as an internal utility, not a configuration surface for the
  prediction.
