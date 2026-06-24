---
name: release-prep
source: content/features/release-prep.md
tags:
- release
- publishing
- quality
type: note
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

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
