---
name: release-prep
source: content/features/release-prep.md
tags:
- release
- publishing
- quality
type: error
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

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
