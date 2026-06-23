---
feature: release-prep
summary: Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds
tags: [release, publishing, quality]
source_globs:
  - src/attune/agents/release/**
nav:
  help: release-prep
  mkdocs:
    how-to: how-to/release-prep
    architecture: architecture/release-prep
    reference: reference/release-prep
---

## Overview

Release-prep is the **deterministic gate** for shipping. A team of four
agents runs **real tools** — `bandit`, `ruff`, `pytest --cov`, and a
docstring/README/CHANGELOG check — in parallel, measures the results
against **hard quality-gate thresholds**, and returns an APPROVED or
BLOCKED verdict. It is the enforcement half of the release pair.

It is the counterpart to **release-notes**, the advisory workflow.
Release-notes *predicts and drafts* (a changelog plus an LLM go/no-go);
release-prep *measures and gates* (real numbers against thresholds).
Reach for release-prep when you need a pass/fail you can trust before
tagging a release or uploading to PyPI.

Two things distinguish release-prep from the SDK workflows:

- **It runs by default at zero API cost.** The agents are rule-based
  (`RELEASE_LLM_MODE` defaults to `"simulated"`) — they parse real tool
  output, not LLM responses. LLM enhancement is opt-in.
- **It is CLI-only.** There is no MCP tool for the gate (that keeps the
  conversational surface advisory). Run it with **`attune workflow run
  release-gate`** (or the canonical slug `release-prep`).

You also reach release-prep through the Python API
(`ReleasePrepTeamWorkflow` / `ReleasePrepTeam`), documented here for
wiring the gate into a release script or CI step.

## Concepts

### Four agents, real tools, run in parallel

`ReleasePrepTeam.assess_readiness` runs four agents concurrently
(`asyncio.gather` over `run_in_executor`). Each runs a real tool and
parses its output into a score and findings:

| Agent | Tool it runs | What it measures |
|-------|--------------|------------------|
| `SecurityAuditorAgent` | `uv run bandit -r src/ -f json --severity-level medium` | Counts vulnerabilities by severity; `critical_issues` = CRITICAL + HIGH. |
| `TestCoverageAgent` | `uv run pytest --co` then `uv run pytest --cov=<target> -x --timeout=30` | Parses the TOTAL coverage percentage; estimates from test count if coverage can't be measured. |
| `CodeQualityAgent` | `uv run ruff check src/ --statistics` | Counts lint violations and maps them to a 0–10 quality score. |
| `DocumentationAgent` | AST walk of `src/**/*.py` | Docstring coverage of public functions, plus README/CHANGELOG presence. |

### Four quality gates, four thresholds

The team evaluates the agent results against `DEFAULT_QUALITY_GATES`.
Three gates are **critical** (a failure blocks release); documentation
is a warning only:

| Gate | Threshold key | Default | Critical? |
|------|---------------|---------|-----------|
| Security | `max_critical_issues` | `0` | Yes — blocks |
| Test Coverage | `min_coverage` | `80.0` | Yes — blocks |
| Code Quality | `min_quality_score` | `7.0` | Yes — blocks |
| Documentation | `min_doc_coverage` | `80.0` | No — warning |

A release is **approved** when no critical gate fails and there are no
blockers. Confidence is `high` (approved, no warnings), `medium`
(approved with warnings), or `low` (not approved).

### Rule-based by default, LLM-enhanced on request

`RELEASE_LLM_MODE` defaults to `"simulated"` — the agents score real
tool output with rule-based logic and make **no** API calls (cost is
$0). Set `RELEASE_LLM_MODE=real` **and** provide an `ANTHROPIC_API_KEY`
to let the security and quality agents send their tool output to an LLM
for nuanced classification (coverage and documentation stay
rule-based). The mode is recorded per agent in `findings["mode"]`.

### Progressive tier escalation

Each agent starts at the `CHEAP` model tier and escalates to `CAPABLE`,
then `PREMIUM`, only if its run reports failure (for the security agent,
"failure" means critical issues remain; for code quality, a score below
threshold). Escalation is most meaningful in `real` LLM mode, where a
stronger model re-analyzes; in the default rule-based mode it re-runs
the same deterministic command. `ReleaseAgentResult.escalated` records
whether escalation happened and `tier_used` records the final tier.

### The assessment always "succeeds"; the verdict is the payload

`ReleasePrepTeamWorkflow.execute` returns a `WorkflowResult` whose
`success` reflects that the assessment **ran** — not the release
verdict. A BLOCKED release still returns `success=True` and exits 0; the
verdict lives in `metadata["approved"]` (and `metadata["confidence"]`),
and the full report is the serialized `WorkflowReport` in
`final_output`. Read the verdict from the report, not from `success`.

### `execute` and `assess_readiness` are async

Both `ReleasePrepTeamWorkflow.execute` and
`ReleasePrepTeam.assess_readiness` are coroutines — `await` them (or
drive them with `asyncio.run`). Calling `assess_readiness` without
awaiting is the most common mistake.

## Quickstart

Run the gate from the CLI at your project root:

```bash
attune workflow run release-gate
```

The output is the readiness report — the verdict (APPROVED / BLOCKED),
the four quality gates with actual-vs-threshold values, a per-agent
breakdown, and any blockers or warnings. The canonical slug
`release-prep` runs the same workflow.

## Tasks

### Gate a release from the CLI

**Goal:** get a pass/fail verdict before tagging a release.

**Steps:**

```bash
# Run the gate at the project root:
attune workflow run release-gate

# JSON output for a CI step:
attune workflow run release-gate --json
```

**Verify:** the slugs are `release-gate` and `release-prep` (both run
`ReleasePrepTeamWorkflow`). `--path` / `-p` defaults to the current
directory; `--json` / `-j` emits machine-readable output. The verdict
is APPROVED or BLOCKED; the run exits 0 even when BLOCKED (the verdict
is data, not the exit code).

### Run the gate from Python

**Goal:** drive the gate from a release script and branch on the
verdict.

**Steps:**

```python
import asyncio

from attune.agents.release import ReleasePrepTeamWorkflow


async def main() -> None:
    workflow = ReleasePrepTeamWorkflow()
    result = await workflow.execute(path=".")

    approved = result.metadata["approved"]
    print("APPROVED" if approved else "BLOCKED", result.metadata["confidence"])
    print(result.summary)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. `result.success` is
`True` whenever the assessment ran; the verdict is
`result.metadata["approved"]`. The full report is in
`result.final_output`.

### Customize the quality-gate thresholds

**Goal:** raise (or lower) the bars the gate enforces.

**Steps:**

```python
import asyncio

from attune.agents.release import ReleasePrepTeam


async def main() -> None:
    team = ReleasePrepTeam(
        quality_gates={"min_coverage": 90.0, "min_quality_score": 8.0},
    )
    report = await team.assess_readiness(codebase_path=".")
    print(report.format_console_output())


asyncio.run(main())
```

**Verify:** `assess_readiness` is a coroutine — `await` it. The
`quality_gates` keys are `max_critical_issues`, `min_coverage`,
`min_quality_score`, and `min_doc_coverage`; any you pass override the
defaults, the rest stay at `DEFAULT_QUALITY_GATES`.

## Reference

Release-prep's public surface is the `ReleasePrepTeamWorkflow` (CLI /
registry adapter) and the `ReleasePrepTeam` coordinator, both importable
from `attune.agents.release`.

### `ReleasePrepTeamWorkflow` — `attune.agents.release`

| Symbol | Purpose |
|--------|---------|
| `ReleasePrepTeamWorkflow(quality_gates=None, **kwargs)` | Construct the registry adapter. `quality_gates` overrides thresholds. |
| `ReleasePrepTeamWorkflow.execute(path=".", context=None, **kwargs)` | **Async.** Run the gate. Maps `target` → `path` for CLI/VSCode. Returns a `WorkflowResult`. |
| `ReleasePrepTeamWorkflow.name` | The canonical slug, `"release-prep"` (synonym `release-gate`). |
| `ReleasePrepTeamWorkflow.stages` | `["triage", "parallel-validation", "synthesis", "decision"]`. |

### `ReleasePrepTeam` — `attune.agents.release`

| Symbol | Purpose |
|--------|---------|
| `ReleasePrepTeam(quality_gates=None, redis_url=None)` | Construct the coordinator. Optional Redis URL for coordination (graceful no-op when unavailable). |
| `ReleasePrepTeam.assess_readiness(codebase_path=".")` | **Async.** Run the four agents in parallel and return a `ReleaseReadinessReport`. |
| `ReleasePrepTeam.get_total_cost()` | Total LLM cost across agents ($0 in the default rule-based mode). |

### Default quality gates

| Gate | Key | Default | Critical |
|------|-----|---------|----------|
| Security | `max_critical_issues` | `0` | Yes |
| Test Coverage | `min_coverage` | `80.0` | Yes |
| Code Quality | `min_quality_score` | `7.0` | Yes |
| Documentation | `min_doc_coverage` | `80.0` | No |

### The four agents

| Agent | Tool | Score basis |
|-------|------|-------------|
| `SecurityAuditorAgent` | bandit (JSON, severity ≥ medium) | Severity-weighted; `critical_issues` = CRITICAL + HIGH. |
| `TestCoverageAgent` | pytest collect + `pytest --cov` | TOTAL coverage %; heuristic estimate as fallback. |
| `CodeQualityAgent` | `ruff check --statistics` | 0–10 by violation count. |
| `DocumentationAgent` | AST docstring walk | Public-function docstring coverage %. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the assessment **ran** (always `True` on a completed run — not the verdict). |
| `final_output` | `dict` | The serialized `WorkflowReport` (verdict callout, gate table, per-agent breakdown, blockers, warnings, next steps). |
| `summary` | `str` | Executive summary — approval status and the failed gates. |
| `metadata` | `dict` | `approved` (bool) and `confidence` (`high` / `medium` / `low`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| CLI | `attune workflow run release-gate [--path <p>] [--json]` (canonical slug `release-prep`). |
| Python | `await ReleasePrepTeamWorkflow().execute(path=<p>)` or `await ReleasePrepTeam().assess_readiness(codebase_path=<p>)`. |

There is **no MCP tool** for the gate — it is CLI / Python only.

## Comparison

Release-prep is the **gate** half of the release pair:

| Workflow | Slug(s) | Kind | What it does |
|----------|---------|------|--------------|
| `release-prep` (this feature) | `release-prep`, `release-gate` | Deterministic gate (agent team) | Runs real bandit / ruff / pytest / docstring checks against hard thresholds; returns APPROVED / BLOCKED. CLI-only; $0 by default. |
| `release-notes` | `release-notes` | Advisory (SDK) | Drafts a changelog + an LLM go/no-go. Does not block. Subscription-billed with depth budget caps. |

Reach for **release-prep** when you need an enforced gate on measured
numbers. Reach for **release-notes** when you want the changelog drafted
and a recommendation. A common flow is release-notes to draft and read
the landscape, then release-prep to gate the actual ship.

When all gates pass, the report's next step points at **secure-release**
(`attune workflow run secure-release`), the composite security pipeline.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'ReleasePrepTeam.assess_readiness' was never awaited` | `assess_readiness` (or `execute`) called without `await` | Both are coroutines — `await` them or use `asyncio.run` | high |
| Verdict is BLOCKED but the command exited 0 | `success` reflects that the assessment ran, not the verdict | Read `metadata["approved"]` / the report — don't gate on the exit code alone | medium |
| Security gate shows `actual: -1` / a gate can't be measured | The agent errored (e.g. the tool raised); `critical_issues` falls back to `-1` | Inspect that agent's `findings["error"]`; confirm the tool runs in the project | medium |
| Coverage reads as estimated, not measured | `pytest --cov` output wasn't parseable (timeout, no TOTAL line) | The percentage is heuristic from test count (`findings["estimated"]` is `True`); run coverage directly to confirm | low |
| A gate reports `"bandit not available"` / `"ruff not available"` | The tool isn't installed in the run environment | Install the tool; the agent scores a neutral fallback otherwise | medium |
| Setting `quality_gates={"coverage": 0.9}` has no effect | Wrong key | Use `min_coverage` (a percentage like `90.0`), not `coverage` | medium |

### Risk areas

- **The async call is easy to get wrong.** `assess_readiness` and
  `execute` are coroutines. Calling `assess_readiness` synchronously is
  the single most common mistake.
- **`success` is not the verdict.** A BLOCKED release returns
  `success=True`. Branch on `metadata["approved"]`.
- **Threshold keys are specific.** They are `max_critical_issues`,
  `min_coverage`, `min_quality_score`, `min_doc_coverage` — coverage and
  doc-coverage are percentages (e.g. `80.0`), not fractions.

### Diagnosis order

1. Confirm you are awaiting: `await workflow.execute(path=".")` /
   `await team.assess_readiness(codebase_path=".")`.
2. Read the verdict from `result.metadata["approved"]`, not `success`.
3. For a blocked gate, read the report's blockers and the failing
   gate's actual-vs-threshold.
4. For an errored agent, inspect its `findings["error"]` in
   `report.agent_results`.
5. Confirm the tools (`bandit`, `ruff`, `pytest`) run in the project
   environment.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What's the difference between release-prep and release-notes?
  **A:** Release-prep is the deterministic gate — it runs real
  bandit/ruff/pytest against hard thresholds and returns APPROVED or
  BLOCKED. Release-notes is advisory — it drafts a changelog and an LLM
  go/no-go and never blocks.
- **Q:** How much does the gate cost?
  **A:** $0 by default. The agents are rule-based
  (`RELEASE_LLM_MODE=simulated`) and make no API calls. LLM enhancement
  is opt-in with `RELEASE_LLM_MODE=real` plus a key.
- **Q:** Why did a BLOCKED run still exit 0?
  **A:** `success` means the assessment ran; the verdict is in
  `metadata["approved"]`. Branch on that, not the exit code.
- **Q:** How do I change the thresholds?
  **A:** Pass `quality_gates={...}` to `ReleasePrepTeam` /
  `ReleasePrepTeamWorkflow` using the keys `max_critical_issues`,
  `min_coverage`, `min_quality_score`, `min_doc_coverage`.
- **Q:** Is there an MCP tool for the gate?
  **A:** No. The gate is CLI / Python only — run `attune workflow run
  release-gate`. The advisory (`release_notes`) is the MCP surface.
- **Q:** Which calls are async?
  **A:** Both `ReleasePrepTeamWorkflow.execute` and
  `ReleasePrepTeam.assess_readiness` are coroutines — `await` them.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `ReleasePrepTeamWorkflow`, `ReleasePrepTeam`, and the
  `ReleaseReadinessReport` it returns. Names with a leading underscore —
  `_evaluate_quality_gates`, `_run_command`, `_execute_tier` — are
  internal.
- **Gate after you draft.** Use release-notes to draft the changelog,
  then release-prep to gate the ship on measured numbers.
- **Keep it free.** The default rule-based mode costs $0. Only set
  `RELEASE_LLM_MODE=real` when you want LLM-nuanced security/quality
  classification.
- **Read the verdict, not the exit code.** `metadata["approved"]` is the
  pass/fail; `success` only says the run completed.

## Design & extension

### Design decisions

- **Deterministic gate, not an advisor.** Release-prep runs real tools
  and measures their output against fixed thresholds, so the verdict is
  reproducible and free. The LLM advisory (changelog + go/no-go) is the
  separate `release-notes` feature — keeping "gate the ship" and "draft
  the notes" distinct.
- **Parallel agents, progressive escalation.** The four agents run
  concurrently and each escalates `CHEAP → CAPABLE → PREMIUM` only on
  failure — bounding cost while still allowing a stronger pass when an
  agent struggles (in `real` LLM mode).
- **The assessment always succeeds; the verdict is data.** `execute`
  returns `success=True` whenever the run completed, with the verdict in
  `metadata` and the full `WorkflowReport` in `final_output`. A blocked
  release is a normal result, not an error.
- **Optional coordination.** Redis (agent heartbeats) and
  `AgentStateStore` (execution history) are optional — both degrade to
  no-ops when unavailable, so the gate runs anywhere.

### Extension points

- **Tune the gates:** pass `quality_gates={...}` (keys
  `max_critical_issues` / `min_coverage` / `min_quality_score` /
  `min_doc_coverage`).
- **Enable LLM enhancement:** set `RELEASE_LLM_MODE=real` with an
  `ANTHROPIC_API_KEY`; the security and quality agents then classify
  their tool output with an LLM.
- **Coordinate across processes:** pass a `redis_url` to
  `ReleasePrepTeam` for heartbeats and completion signals.
- **Add an agent:** subclass `ReleaseAgent`, implement `_execute_tier`
  to run a tool and return `(success, findings)`, and add it to the
  team's agent list plus a gate in `_evaluate_quality_gates`.
