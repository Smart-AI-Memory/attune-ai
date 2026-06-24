---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: note
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

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
