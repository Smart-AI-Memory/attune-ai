---
feature: release-notes
summary: Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents
tags: [release, changelog, advisory]
source_globs:
  - src/attune/workflows/release_prep.py
nav:
  help: release-notes
  mkdocs:
    how-to: how-to/release-notes
    architecture: architecture/release-notes
    reference: reference/release-notes
---

## Overview

Release-notes drafts a changelog and an overall readiness
recommendation for a codebase about to ship. It is **SDK-native**:
`ReleasePreparationWorkflow` delegates to four Claude Agent SDK
subagents — a health checker, a security scanner, a changelog
generator, and a release assessor — and synthesizes their findings
into one report with a readiness score, a go/no-go recommendation, a
drafted changelog, and prioritized next steps.

It is the **advisory** half of the release pair. Release-notes
*predicts and drafts*; it does **not** enforce hard quality gates and
it does not block. The deterministic gate — real `bandit` / `ruff` /
`pytest` runs measured against pass/fail thresholds — is the separate
**release-prep** agent team (`ReleasePrepTeamWorkflow`), reached as
`attune workflow run release-gate`. Reach for release-notes to *write
the changelog and get a recommendation*; reach for release-prep to
*gate the release on measured numbers*.

You reach release-notes these ways:

- the **`release_notes` MCP tool**, inside a Claude Code conversation
  (the `/release` skill is the conversational front door) — drafts a
  changelog and a go/no-go advisory;
- the CLI — **`attune workflow run release-notes`**;
- the Python API — `await ReleasePreparationWorkflow().execute(...)`,
  documented here for wiring the advisory into a hook or a release
  pipeline.

The reliable programmatic surfaces are the CLI and the Python API
(see *Reaching release-notes reliably* below).

## Concepts

### Four subagents, one report

`ReleasePreparationWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define four subagents. The
orchestrator runs at the `CAPABLE` model tier; each subagent focuses
on its own release-readiness domain:

| Subagent | Domain | Tools | What it reports |
|----------|--------|-------|-----------------|
| `health-checker` | Health | Read / Glob / Grep / Bash | Test results, dependency and lock-file status, CI pipeline health — each with a pass/fail status and remediation. |
| `security-scanner` | Security | Read / Glob / Grep | Dependency vulnerabilities, outdated packages with CVEs, hardcoded secrets, eval/exec, and path-traversal risks — each with severity and a fix. |
| `changelog-generator` | Changelog | Read / Glob / Grep / Bash | A draft CHANGELOG section in Keep a Changelog format, built from `git log` since the last release tag. |
| `release-assessor` | Assessment | Read / Glob / Grep | Coverage, doc completeness, version bumps, migration guides, and any blockers — plus a go/no-go recommendation. |

The orchestrator then synthesizes the four into one report with five
sections — **Summary** (a 0–100 readiness score and a 2–3 sentence
go/no-go executive summary), **Health**, **Security**, **Changelog**
(the drafted notes), and **Suggestions** (actionable next steps
ordered by priority, including any release blockers).

### Advisory, not a gate

Release-notes returns a recommendation; it does not stop anything. The
readiness score and go/no-go come from an LLM assessor reading the
codebase, not from measured thresholds. Treat the output as input to
your decision — for an enforced gate that fails on real numbers, run
`release-prep` (the agent team) via `attune workflow run release-gate`.

### Depth controls turns and the budget cap

`execute` takes a `depth` of `"quick"`, `"standard"` (default), or
`"deep"`. Depth maps to both the maximum agent turns and a per-run USD
budget cap:

| Depth | Max agent turns | Default budget cap |
|-------|-----------------|--------------------|
| `quick` | 10 | $2 |
| `standard` | 20 | $10 |
| `deep` | 40 | $25 |

An unrecognized depth falls back to the standard budget (20 turns).
The cap is a cost ceiling for API-key users and a complexity bound for
subscription users (who pay no per-request cost). Override it with
`ATTUNE_MAX_BUDGET_USD` — set it to `0` to disable the cap entirely
for a pre-release run that needs to finish.

### `execute` is async

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake. It reads two keyword arguments: `path` (required) and `depth`
(default `"standard"`). An empty or missing `path` returns a failed
`WorkflowResult` ("path argument is required") rather than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`). The
synthesized report lands in `final_output` — a serialized report when
the findings parse, or the raw markdown otherwise — with a short
`summary`, a `suggestions` list, the `cost_report`, the `provider`,
and a `metadata` dict echoing `path`, `depth`, and `max_turns`. On
failure, `success` is `False` and `error` carries the reason.

### Reaching release-notes reliably

Drive release-notes through the **CLI** (`attune workflow run
release-notes --path <p>`) or the **Python API**
(`ReleasePreparationWorkflow().execute(path=<p>)`) — both pass the
`path` the workflow expects. The `release_notes` MCP tool is the
conversational front door. (If you call the workflow directly, pass
`path` — the documented kwarg.)

## Quickstart

Draft release notes for a project and print the result.
`ReleasePreparationWorkflow.execute` is an async coroutine, so drive
it with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".")

    print(result.success)          # True on a completed run
    print(result.summary)          # readiness score + go/no-go
    print(result.final_output)     # the synthesized report + changelog


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path=".")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the fullest
treatment.

## Tasks

### Draft release notes from the CLI

**Goal:** draft a changelog and get a go/no-go recommendation without
writing any Python.

**Steps:**

```bash
# Default depth (standard) at the project root:
attune workflow run release-notes --path .

# Deep advisory, JSON output:
attune workflow run release-notes --path . --depth deep --json
```

**Verify:** the slug is `release-notes`. `--path` / `-p` defaults to
the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use `attune
workflow info release-notes` to confirm registration. The report
includes a readiness score, the drafted changelog, and prioritized
next steps — this is advice, not a gate.

### Draft release notes from Python

**Goal:** wire the advisory into a release hook or pipeline and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="deep")

    if not result.success:
        print("advisory failed:", result.error)
        return

    print(result.final_output)     # synthesized report + changelog
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the report in `final_output`; a failure
returns `success=False` with a populated `error`. `metadata` echoes
the `path`, `depth`, and `max_turns`.

### Keep the advisory cheap

**Goal:** run the advisory at the lowest cost.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="quick")
    print(result.summary)


asyncio.run(main())
```

**Verify:** `quick` uses the smallest agent-turn budget (10) and the
lowest cap ($2). To let a deep pre-release run finish without a cap,
export `ATTUNE_MAX_BUDGET_USD=0`. Subscription users pay no
per-request cost regardless.

## Reference

Release-notes' public surface is the `ReleasePreparationWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `ReleasePreparationWorkflow` — `attune.workflows.release_prep`

| Symbol | Purpose |
|--------|---------|
| `ReleasePreparationWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `ReleasePreparationWorkflow.execute(**kwargs)` | **Async.** Draft release notes + advisory. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). Returns a `WorkflowResult`. |
| `ReleasePreparationWorkflow.name` | The registered slug, `"release-notes"`. |
| `ReleasePreparationWorkflow.stages` | `["agent-prep"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → turns and budget

| Depth | Max turns | Budget cap | Use when |
|-------|-----------|------------|----------|
| `quick` | 10 | $2 | A fast pass for an early read. |
| `standard` | 20 | $10 | The default — balanced coverage and cost. |
| `deep` | 40 | $25 | The fullest treatment before a major release. |

### The four subagents

| Subagent | Role |
|----------|------|
| `health-checker` | Runs tests, checks dependency/lock status, verifies CI. |
| `security-scanner` | Flags vulnerabilities, secrets, eval/exec, path traversal. |
| `changelog-generator` | Drafts a Keep a Changelog section from `git log`. |
| `release-assessor` | Judges overall readiness and gives a go/no-go. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | The synthesized report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Readiness score + go/no-go overview. |
| `suggestions` | `list[NextAction]` | Prioritized next steps, including blockers. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` | `str \| None` | Failure reason. (`error_type` and `transient` exist on `WorkflowResult` but this workflow's failure path leaves them unset.) |

### Entry points

| Surface | Invocation |
|---------|------------|
| MCP tool | `release_notes(path=<p>)` — changelog draft + go/no-go advisory (reached via the `/release` skill). |
| CLI | `attune workflow run release-notes --path <p> [--depth quick\|standard\|deep] [--json]`. |
| Python | `await ReleasePreparationWorkflow().execute(path=<p>, depth=<d>)`. |

## Comparison

Release-notes is the **advisory** half of the release pair. The two
share the "release prep" idea but differ in kind:

| Workflow | Slug(s) | Kind | What it does |
|----------|---------|------|--------------|
| `release-notes` (this feature) | `release-notes` | Advisory (SDK) | Drafts a changelog + an LLM go/no-go. Does not block. Subscription-billed with depth budget caps. |
| `release-prep` | `release-prep`, `release-gate` | Deterministic gate (agent team) | Runs real `bandit` / `ruff` / `pytest` / docstring checks against hard thresholds and returns an APPROVED / BLOCKED verdict. CLI-only. |

Reach for **release-notes** when you want the changelog written and a
recommendation. Reach for **release-prep** (`attune workflow run
release-gate`) when you need an enforced gate on measured numbers. A
common flow is release-notes to draft the notes and read the
landscape, then release-prep to gate the actual ship.

Two adjacent tools the `/release` skill also exposes: `dependency_check`
(dependency audit / vulnerability scan) and `secure_release` (the
composite security pipeline).

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'ReleasePreparationWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with an empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity and retry | medium |
| Advisory stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower `depth`, or raise the cap with `ATTUNE_MAX_BUDGET_USD` | medium |
| The release shipped despite a "no-go" | Release-notes is advisory — it never blocks | Use `release-prep` (`attune workflow run release-gate`) for an enforced gate | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the main
  public method and it is a coroutine. Forgetting to `await` it is the
  single most common mistake.
- **Advisory ≠ gate.** The go/no-go is a recommendation from an LLM
  assessor, not a measured pass/fail. Don't wire it into CI as a
  blocking check — use `release-prep` for that.
- **Pass `path`.** `execute` reads `path` (and `depth`); the CLI and
  Python API supply `path` correctly.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path=".")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error`.
3. If `error` is "path argument is required", confirm you passed
   `path=`.
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`, `depth`,
   and `max_turns`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these author-curated
> seeds — merged, deduplicated, and frequency-ranked by the FAQ
> Generator (see doc-stack D3, and the help-docs-single-source spec's
> decisions.md D6). This section is **not** projected verbatim as the
> FAQ; it contributes the feature's author-curated seed questions.

- **Q:** What's the difference between release-notes and release-prep?
  **A:** Release-notes is advisory — it drafts a changelog and an LLM
  go/no-go, and never blocks. Release-prep is the deterministic gate:
  it runs real bandit/ruff/pytest against hard thresholds and returns
  APPROVED or BLOCKED. Run the gate with `attune workflow run
  release-gate`.
- **Q:** Does release-notes block my release if the score is low?
  **A:** No. It only recommends. For an enforced gate, use
  release-prep.
- **Q:** How much does a run cost?
  **A:** It's subscription-billed with a per-depth budget cap ($2 /
  $10 / $25 for quick / standard / deep). Subscription users pay no
  per-request cost; set `ATTUNE_MAX_BUDGET_USD=0` to lift the cap.
- **Q:** Which calls are async?
  **A:** `execute` is a coroutine — `await` it or use `asyncio.run`.
- **Q:** Where does the changelog come from?
  **A:** The `changelog-generator` subagent reads `git log` since the
  last release tag and drafts a Keep a Changelog section.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `ReleasePreparationWorkflow` and its async `execute`, and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_prep`, `_SUBAGENT_NAMES`, `_DEPTH_MAX_TURNS` — are
  internal and may change.
- **Draft, then gate.** Use release-notes to write the changelog and
  read readiness, then run `release-prep` (`release-gate`) to gate the
  actual ship on measured numbers.
- **Use `depth` to trade coverage against cost.** A `quick` pass is
  far cheaper than a `deep` one; `ATTUNE_MAX_BUDGET_USD=0` lifts the
  cap when a pre-release run must finish.
- **Take the changelog from `final_output`.** Release-notes returns
  the drafted notes in the result; review and place them.

## Design & extension

### Design decisions

- **SDK-native, four readiness domains.** Release-notes is a single
  `claude_agent_sdk.query` with four subagents — a `health-checker`, a
  `security-scanner`, a `changelog-generator`, and a `release-assessor`
  — each reporting under its own heading. Splitting the domains keeps
  each subagent's context focused; the orchestrator merges them into
  one report.
- **Advisory, not enforcement.** Release-notes predicts and drafts; it
  returns a recommendation rather than a pass/fail verdict. The
  deterministic gate (real tools + hard thresholds) is the separate
  `release-prep` agent team — keeping "draft the notes" and "gate the
  ship" as two distinct features.
- **Depth caps both turns and spend.** Each depth maps to a max-turn
  count and a USD budget cap, so an advisory run is bounded in both
  agent work and cost; `ATTUNE_MAX_BUDGET_USD` overrides the cap.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI, MCP tool,
  and Python surfaces render that same result.

### Extension points

- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost, or set
  `ATTUNE_MAX_BUDGET_USD`.
- **Scope the run:** point `path` at the project root you want
  assessed.
- **Retarget a subagent's model:** `get_subagent_model` honors
  `ATTUNE_AGENT_MODEL_<KEYWORD>` / `ATTUNE_AGENT_MODEL_DEFAULT`, so a
  run can push subagents onto a cheaper or stronger model (the
  `--cheap` CLI flag sets the default to Haiku).
- **Add a readiness domain:** the subagent definitions are built
  inline in `_run_agent_prep`, with the names listed in
  `_SUBAGENT_NAMES`; a new domain is a new `AgentDefinition` plus a
  synthesis section in the task template in `release_prep.py`.
