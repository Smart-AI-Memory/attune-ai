---
type: tip
name: release-prep-tip
feature: release-prep
depth: tip
generated_at: 2026-06-23T21:32:41.155408+00:00
source_hash: 63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2
status: generated
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

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
