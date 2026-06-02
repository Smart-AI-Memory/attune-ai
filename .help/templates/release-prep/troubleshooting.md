---
type: troubleshooting
name: release-prep-troubleshooting
feature: release-prep
depth: troubleshooting
generated_at: 2026-06-02T10:56:02.714048+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Troubleshoot release prep

Release prep coordinates four specialized agents — health checker, security scanner, changelog generator, and release assessor — and aggregates their results into a `ReleaseReadinessReport`. Most failures fall into one of the categories below.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `assess_readiness()` returns `approved: False` with no `blockers` | Inspect each `QualityGate` in `report.quality_gates` — a gate with `passed: False` and `critical: True` will block approval even if `blockers` is empty |
| An agent result has `success: False` but `score: 0.0` and `findings: {}` | The agent likely raised before writing results; check the `agent_id` and `agent_role` fields to identify which agent failed, then run it directly via `ReleaseAgent.process()` |
| `confidence` on the report is unexpectedly low | One or more agents escalated to a higher tier (`escalated: True` in `ReleaseAgentResult`); this usually means the cheaper tier timed out or returned unusable output |
| `TestCoverageAgent` fails or returns no coverage data | Confirm `pytest --cov` runs cleanly in your environment: `pytest --cov . --cov-report=term-missing` |
| `CodeQualityAgent` findings are empty or missing | Confirm `ruff` is installed and on `PATH`: `ruff check . --output-format=json` |
| `total_cost` from `ReleasePrepTeam.get_total_cost()` is much higher than expected | An agent escalated from CHEAP to CAPABLE or PREMIUM; check `tier_used` and `escalated` on the relevant `ReleaseAgentResult` entries |
| `ReleasePrepTeamWorkflow.execute()` hangs | Check whether Redis is reachable; `ReleasePrepTeam` accepts a `redis_url` and may be waiting on a connection that never resolves |
| The report's `quality_gates` list is empty | `ReleasePrepTeam` was initialized without custom `quality_gates` and the defaults were not applied; pass an explicit `quality_gates` dict to `ReleasePrepTeam(quality_gates={...})` |

## Step-by-step diagnosis

1. **Print the full report to the console.**
   Call `report.format_console_output()` on the returned `ReleaseReadinessReport`. This surfaces all `blockers`, `warnings`, and per-gate `message` strings in one pass, and is cheaper than enabling debug logging.

2. **Serialize the report and inspect every field.**
   Call `report.to_dict()` and pretty-print it. Check `agent_results` for any entry where `success: False`, and check `quality_gates` for any entry where `passed: False`. The `message` field on a failed `QualityGate` usually names the exact issue.

3. **Reproduce the failure against a single agent.**
   Instantiate only the agent that failed and call `process()` directly on your codebase path:

   ```python
   from release.release_agents import TestCoverageAgent  # or CodeQualityAgent, DocumentationAgent, SecurityAuditorAgent

   agent = TestCoverageAgent()
   result = agent.process(codebase_path='.')
   print(result.success, result.score, result.findings)
   ```

   This isolates the failure from the parallel orchestration in `ReleasePrepTeam`.

4. **Check whether the underlying tool is the real failure.**
   Each agent shells out to an external tool. Run the tools directly to rule out environment issues:

   ```bash
   # TestCoverageAgent
   pytest --cov . --cov-report=term-missing

   # CodeQualityAgent
   ruff check . --output-format=json
   ```

   If the tool itself fails, the agent result will reflect that failure regardless of what release prep does.

5. **Inspect `execution_time_ms` and `tier_used` per agent.**
   High `execution_time_ms` or an unexpected `tier_used` value (e.g., PREMIUM when you expect CHEAP) tells you which agent triggered tier escalation. Escalation happens automatically when a lower tier times out or returns low-confidence output — it is not a bug, but it does increase `total_cost`.

6. **Run the full workflow with a minimal path.**
   If you can't reproduce the failure on a single agent, try `ReleasePrepTeamWorkflow.execute()` on a small subdirectory to confirm the orchestration layer is not the source of the problem:

   ```python
   from release.release_prep_team import ReleasePrepTeamWorkflow

   workflow = ReleasePrepTeamWorkflow()
   report = workflow.execute(path='./src/mypackage')
   print(report.format_console_output())
   ```

## Common fixes

**A critical quality gate is blocking approval.**
Inspect the failing gate:

```python
for gate in report.quality_gates:
    if not gate.passed and gate.critical:
        print(gate.name, gate.threshold, gate.actual, gate.message)
```

Raise the `actual` value above `threshold` (fix failing tests, improve coverage, resolve lint errors) or, if the threshold is misconfigured, pass corrected thresholds when constructing `ReleasePrepTeam`:

```python
team = ReleasePrepTeam(quality_gates={'coverage': 0.80, 'security': 0.90})
```

**`TestCoverageAgent` reports no coverage or crashes.**
`pytest --cov` must be installed and your package must be discoverable. Install the missing dependency:

```bash
pip install pytest-cov
```

Then confirm the coverage report runs outside release prep before retrying.

**`CodeQualityAgent` returns empty findings.**
`ruff` must be on `PATH`. Install it if missing:

```bash
pip install ruff
```

**Redis connection hangs.**
If you pass a `redis_url` to `ReleasePrepTeam` or `ReleasePrepTeamWorkflow`, verify connectivity before running:

```bash
redis-cli -u "$REDIS_URL" ping
```

If Redis is unavailable and you don't need distributed state, omit `redis_url` entirely — both classes accept `None`.

**Tier escalation inflating cost.**
If `ReleaseAgent` is escalating unexpectedly, check that your environment can complete the CHEAP-tier call within its timeout. Escalation to CAPABLE or PREMIUM is automatic when the cheaper tier fails; there is no flag to disable it, but fixing the underlying tool failure (coverage not found, ruff not installed) will prevent unnecessary escalation.

**Report fields are missing or zero after a successful run.**
`ReleaseReadinessReport` fields like `total_duration` and `total_cost` default to `0.0`. If they remain zero after a real run, the agents may have returned before writing those values — confirm each `ReleaseAgentResult.execution_time_ms` and `cost` are non-zero, and check that `ReleasePrepTeam.get_total_cost()` returns the expected sum.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
