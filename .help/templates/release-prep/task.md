---
type: task
name: release-prep-task
feature: release-prep
depth: task
generated_at: 2026-06-11T04:39:32.872298+00:00
source_hash: b484e3b8f8e27e1e37d71dd39e93de2e14c056d5969f51d404e9b11858bd81b7
status: generated
scaffold_hash: 27a90574d75339f2fab8f7a1a95121920a49e38a867a7c39451f9987629e9532
---

# Work with release prep

Use `ReleasePrepTeam` when you need an objective go/no-go recommendation before cutting a release tag — it runs health checks, security scanning, documentation review, and changelog generation in parallel and aggregates the results into a single `ReleaseReadinessReport`.

## Prerequisites

- A local checkout of the codebase you want to assess
- The `release` package available in your Python environment

## Run a release readiness assessment

1. **Instantiate `ReleasePrepTeam`.**

   ```python
   from release import ReleasePrepTeam

   team = ReleasePrepTeam()
   ```

   To tighten or relax thresholds, pass a `quality_gates` dict at construction time:

   ```python
   team = ReleasePrepTeam(quality_gates={"test_coverage": 0.85, "code_quality": 0.80})
   ```

2. **Call `assess_readiness` against your codebase path.**

   ```python
   report = team.assess_readiness(codebase_path=".")
   ```

   This coordinates four agents — `health-checker`, `security-scanner`, `changelog-generator`, and `release-assessor` — and returns a `ReleaseReadinessReport`. Each agent produces a `ReleaseAgentResult` containing a `score`, a `confidence` value, and a `findings` dict. Agents that need deeper analysis automatically escalate through model tiers (CHEAP → CAPABLE → PREMIUM); the tier used is recorded in the `tier_used` field of each result.

3. **Print the formatted report.**

   ```python
   print(report.format_console_output())
   ```

4. **Review blockers and warnings.**

   Entries in `report.blockers` must be resolved before release. Entries in `report.warnings` are non-critical but worth addressing:

   ```python
   for blocker in report.blockers:
       print(f"BLOCKER: {blocker}")

   for warning in report.warnings:
       print(f"WARNING: {warning}")
   ```

5. **Serialize the report for CI pipelines (optional).**

   ```python
   import json

   with open("release-readiness.json", "w") as f:
       json.dump(report.to_dict(), f, indent=2)
   ```

## Confirm success

The assessment passes when `report.approved` is `True` and `report.blockers` is empty. To see the detail behind the verdict, inspect `report.quality_gates`: each `QualityGate` exposes the gate's `threshold`, the measured `actual` value, and whether it `passed`. Any gate where `critical` is `True` and `passed` is `False` sets `report.approved` to `False`.

## Key files

- `src/attune/workflows/release_prep.py` — `ReleasePrepTeamWorkflow`, `ReleasePreparationWorkflow`
- `src/attune/agents/release/release_prep_team.py` — `ReleasePrepTeam`
- `src/attune/agents/release/release_models.py` — `ReleaseReadinessReport`, `QualityGate`, `ReleaseAgentResult`
