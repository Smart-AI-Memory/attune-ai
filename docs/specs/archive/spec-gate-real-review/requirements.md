# Spec: Real spec quality gates + dead orchestration-engine removal

**Status:** complete (2026-06-26) — gate made real in #1094 (dogfood R1/R2), dead engine removed in #1096 (pre-removal tag); deferred docs handled by orchestration-doc-fiction-cleanup
**Owner:** Patrick + agent
**Supersedes scope of:** the Phase B half of
`interactive-orchestration-access` (Phase A shipped as #1093)

---

## Problem

The `/spec` quality gate is silent theater. Running `/spec` and
executing tasks calls (with `skip_gates=False`, the default):

```text
execute_with_approval(skip_gates=False)
  -> PipelineOrchestrator.run_all()
    -> run_gates_for_task()           # gates run by default
      -> _run_quality_gate(task)      # builds code_reviewer + security_auditor team
        -> DynamicTeamBuilder.build_from_plan()
          -> StubAgent                # the only agent the builder makes
            -> StubAgent.process() -> SDKAgentResult(success=True, cost=0)
```

`StubAgent.process()` returns unconditional success with no work —
no LLM call, no review, cost 0. So every `/spec` task's "quality
gate" (a code review + security audit with 70.0 thresholds) passes
without performing any review. The `StubAgent` docstring even claims
it raises `NotImplementedError`; the code is worse — it fakes a pass.

This is the "registered != working / fake-success stub" failure mode
that `.claude/rules/attune/removing-dead-code.md` was written about.
The dead `DynamicTeam` engine is not merely unused — it is wired into
a live, user-facing feature that silently no-ops.

### Premise correction

The prior Phase B handoff framed this as "remove the dead
orchestration engine" and listed targets that are in fact **live**.
Grepping the actual call sites (per the "spec scope drifts from code
reality" lesson) shows the starter's target list was wrong; the true
dead/live split is recorded in `decisions.md`. Blanket-deleting the
handoff's list would break `main` (e.g. removing `execution_strategies`
breaks the live `health-check` workflow).

---

## Goals

1. **Make the gate real.** `_run_quality_gate` must perform an actual
   code review + security audit using the already-live
   `CodeReviewWorkflow` and `SecurityAuditWorkflow`, and gate on their
   real scores against the existing thresholds.
2. **Remove the dead engine** that the fake gate was the last consumer
   of: `StubAgent`, `dynamic_team`, `team_builder`,
   `workflow_composer`, `workflow_agent_adapter`, the orchestration
   `meta_orchestrator`, `multi_agent_mixin`, the `workflows/base.py`
   multi-agent params, and the dead `TaskDecomposer.decompose()` LLM
   path.
3. **Preserve everything live** (see decisions.md "KEEP LIVE").
4. **Record the corrected classification** in `decisions.md` so the
   removal is auditable and the premise correction is durable.

---

## Non-goals

- Building a general agent-team feature. If teams are wanted later,
  generalize the working `ReleasePrepTeam` / `agent_factory`, not the
  deleted `SDKAgent` (per removing-dead-code.md).
- Touching `execution_strategies` / `_strategies`,
  `progressive.MetaOrchestrator`, `agent_templates` data exports, or
  `TaskDecomposer._parse_tasks_from_xml` — all live.

---

## End state (Done when)

- `/spec` task gates call real review workflows; a deliberately-bad
  task fails its gate (dogfood receipt, not a mocked test).
- The dead engine modules are deleted; `attune.orchestration` public
  surface pruned to what remains live.
- No import of the deleted modules remains in `src/`, `plugin/`, or
  `tests/`; `python -c "import attune.orchestration"` succeeds and the
  full suite is green.
- `health-check` / `orchestrated-health-check` still run (regression
  proof that the live strategies survived).
- Pre-removal tag pushed; `decisions.md` final; CHANGELOG entry
  (this is a breaking removal of public orchestration symbols ->
  minor/major bump per semver policy).

---

## Acceptance criteria

| # | Criterion | Verify |
|---|-----------|--------|
| R1 | Gate performs real review | Dogfood: bad task scores < 70, gate fails |
| R2 | Gate honest on error | Review workflow raising -> gate fails closed, not fake-pass |
| R3 | Dead engine gone | `grep -rn "StubAgent\|DynamicTeam" src/` empty |
| R4 | Live strategies intact | `health-check` workflow runs end-to-end |
| R5 | Spec engine intact | `/spec` of a trivial task completes |
| R6 | Clean imports | `import attune.orchestration` + full suite green |
| R7 | Auditable | decisions.md records dead/live split + premise correction |
