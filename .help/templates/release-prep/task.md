---
type: task
name: release-prep-task
feature: release-prep
depth: task
generated_at: 2026-06-23T21:32:41.155408+00:00
source_hash: 63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2
status: generated
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

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
