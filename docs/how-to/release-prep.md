# Release Prep

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

<!-- attune-generated: source_hash=63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2 feature=release-prep kind=how-to generated_at=2026-06-23 -->
