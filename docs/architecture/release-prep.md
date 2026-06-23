# Release Prep

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

<!-- attune-generated: source_hash=63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2 feature=release-prep kind=architecture generated_at=2026-06-23 -->
