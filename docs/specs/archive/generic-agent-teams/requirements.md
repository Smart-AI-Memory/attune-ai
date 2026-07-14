# Spec: Generic parallel agent teams

**Status:** complete (2026-06-26) — shipped in PR #1098 (src/attune/agents/team.py verified on disk 2026-07-14); reconciled at 2026-07-14 triage (was: APPROVED)
**Owner:** Patrick + agent
**Fulfills the deferred non-goal of:**
`spec-gate-real-review` ("Building a general agent-team feature …
generalize the working `ReleasePrepTeam`, not the deleted `SDKAgent`")

---

## Problem

Two live code paths run a parallel set of analysis workflows,
aggregate their scores, and gate on the result — and each
re-implements the same fan-out/aggregate/gate logic inline:

- **`ReleasePrepTeam`** (`agents/release/release_prep_team.py`) —
  four agents (`SecurityAuditor`, `TestCoverage`, `CodeQuality`,
  `Documentation`) run via `asyncio.gather` + `run_in_executor`,
  then `_evaluate_quality_gates` applies thresholds.
- **The `/spec` quality gate** (`pipeline/orchestrator.py::
  _run_quality_gate`, post-#1094) — instantiates `CodeReviewWorkflow`
  + `SecurityAuditWorkflow`, runs them over each task's files via
  `asyncio.gather`, extracts 0–100 scores, fails **closed** on error,
  and gates on min-score thresholds.

The `/spec` gate is, structurally, a hardcoded two-agent parallel
team. `ReleasePrepTeam` is the same pattern with four agents and a
reusable escalation/state/heartbeat base (`ReleaseAgent`,
`AgentStateStore`). The team abstraction already exists — it is just
welded to one use case and duplicated inline at the other.

There is no reusable way to say "run these N workflows as a team and
gate on their scores." Each new consumer copies the gather/aggregate
glue.

### Why this is not the engine that was removed

This spec deliberately **generalizes the working sibling**, per
`.claude/rules/attune/removing-dead-code.md`. The deleted
`DynamicTeam`/`StubAgent` engine (removed in #1096; see
`docs/specs/spec-gate-real-review/decisions.md`) was a fake-success
stub with orphaned motivation — `StubAgent.process()` returned
`success=True, cost=0, findings={}` and did no work. The `ReleaseAgent`
base does real work (shells out to bandit/pytest/ruff, real LLM calls
with cost tracking, real tier escalation). v1 lifts the **proven**
base, never resurrects the stub.

---

## Goals

1. **Extract a generic `WorkflowAgent` base** from `ReleaseAgent` —
   tier escalation, optional LLM call, Redis heartbeat, and
   `AgentStateStore` persistence — whose unit of work is a
   `BaseWorkflow` run over a target path, yielding a 0–100 score.
2. **Extract a generic `AgentTeam` coordinator** from
   `ReleasePrepTeam` — takes an explicit list of agents plus a
   declarative gate spec, runs them in parallel (fan-out only),
   aggregates scores, and produces a pass/fail verdict with
   blockers/warnings.
3. **Make the `/spec` quality gate the first real consumer.**
   `_run_quality_gate` becomes an `AgentTeam` of a `code-review`
   agent + a `security-audit` agent over the task's files, gated on
   the existing thresholds — replacing the inline gather glue with
   the shared abstraction.
4. **Re-seat `ReleasePrepTeam` on the generic base** so it becomes
   one configuration of `AgentTeam`, proving the abstraction covers
   the richer four-agent case without behavior change.

---

## Non-goals

- **Sequential / DAG topology.** v1 is parallel fan-out only
  (decision D2). Pipelines where stage N feeds stage N+1 are deferred
  to a follow-up; no plan/DAG representation in v1.
- **A user-facing `/team` CLI or MCP run surface.** v1 is library
  infrastructure with two live in-process consumers. A user-facing
  "run an ad-hoc team" command is a separate spec with its own
  motivation (avoiding the run-surface-for-an-unproven-engine pattern
  that got reversed in #1093).
- **Reviving any deleted symbol.** `SDKAgent`, `StubAgent`,
  `DynamicTeam`, `team_builder`, `workflow_composer`,
  `meta_orchestrator` stay deleted. If a behavior is wanted, it is
  rebuilt on the working base, not restored.
- **Changing `AgentStateStore` / `AgentRecoveryManager`.** Reused
  as-is.

---

## Decisions already made (carried into design)

- **D1 — Agent unit of work is a `BaseWorkflow`.** Each agent wraps a
  registered workflow; `_execute_tier` runs it and extracts its score.
  Maximum leverage — reuses all workflow infra and matches what the
  fixed `/spec` gate already does ad-hoc.
- **D2 — Parallel fan-out only for v1.** `asyncio.gather` + aggregate
  + gate, exactly like `ReleasePrepTeam` today. Ship and dogfood this
  before adding any sequential/DAG complexity.
- **D3 — First consumer is the `/spec` quality gate.** Live,
  already-dogfooded on every `/spec` run; no orphaned-motivation risk.

---

## End state (Done when)

- A generic `WorkflowAgent` + `AgentTeam` exist (location settled in
  design.md), each agent wrapping a `BaseWorkflow` and the team running
  agents in parallel with a declarative gate spec.
- `/spec`'s `_run_quality_gate` runs through `AgentTeam`
  (`code-review` + `security-audit`) and preserves current behavior:
  bad task → gate fails; review error → fails closed, never fake-pass.
- `ReleasePrepTeam` is re-seated on `AgentTeam` (or documented why
  not) with no change to its observable `release-prep` output.
- A **non-mocked** dogfood receipt: a real `AgentTeam` of `code-review`
  + `security-audit` run over a deliberately-bad file returns a
  **blocked** verdict with real scores < threshold and non-zero cost.
- `decisions.md` records D1–D3, the generalize-don't-revive constraint,
  and the chosen module location; references the #1096 reversal.
- Full suite green; `health-check` still runs (no collateral damage to
  live strategies).

---

## Acceptance criteria

| # | Criterion | Verify |
|---|-----------|--------|
| R1 | Generic base does real work | `WorkflowAgent` runs a `BaseWorkflow` and returns its real 0–100 score (not a stub constant) |
| R2 | Team runs parallel + gates | `AgentTeam` runs N agents via `asyncio.gather`, aggregates, applies declarative thresholds |
| R3 | `/spec` gate re-seated | `_run_quality_gate` builds an `AgentTeam`; trivial task still completes |
| R4 | Gate honest on error | A review workflow raising → gate fails closed, not fake-pass (preserves #1094 behavior) |
| R5 | Non-mocked dogfood | Real `code-review` + `security-audit` team on a bad file → blocked, scores < threshold, cost > 0 |
| R6 | ReleasePrepTeam (fallback taken) | `release-prep` output unchanged. Full re-seat fallback taken — see D9: heterogeneous gate comparators (max-gate, 0–10 scale, per-finding keys) make a faithful re-seat add v1 `GateSpec` surface for zero behavior change; `QualityGate` is already the single shared definition both consumers import |
| R7 | No revived dead code | `grep -rn "StubAgent\|DynamicTeam\|SDKAgent" src/` stays empty |
| R8 | No collateral damage | `health-check` runs; `import attune.orchestration` clean; full suite green |
| R9 | Auditable | decisions.md records D1–D3 + generalize-not-revive + module location, references #1096 |

---

## Open questions (resolve in design.md)

- **OQ1 — Module home.** Does the generic team live in
  `attune.orchestration` (the natural namespace, but recently pruned
  and semantically loaded by the dead engine) or `attune.agents`
  (where the working base already lives)? Leaning `attune.agents`.
- **OQ2 — Score extraction contract.** `_run_quality_gate` already has
  `_extract_score` / `_SCORE_RE` fallback parsing. Does `WorkflowAgent`
  own a single canonical "score from a `WorkflowResult`" extractor that
  both consumers share, or does each agent supply its own scorer?
- **OQ3 — Gate spec shape.** Reuse `ReleasePrepTeam`'s `QualityGate`
  dataclass + threshold dict, or a slimmer declarative spec now that
  there is no team-plan indirection?
- **OQ4 — Sync vs async agents.** `ReleaseAgent.process()` is sync
  (offloaded via `run_in_executor`); workflows are async. Settle
  whether `WorkflowAgent` is natively async (gather directly) or keeps
  the executor shim for parity with the sync release agents.

---

## Cross-references

- `.claude/rules/attune/removing-dead-code.md` — the
  generalize-the-working-sibling rule this spec follows.
- `docs/specs/spec-gate-real-review/decisions.md` — the #1096 dead-
  engine reversal and the deferred non-goal this spec fulfills.
- `docs/specs/interactive-orchestration-access/decisions.md` — the
  #1093 reversal (run-surface-for-dead-engine), motivating the
  no-`/team`-CLI non-goal.
- Working base to generalize: `agents/release/base_agent.py`
  (`ReleaseAgent`), `agents/release/release_prep_team.py`
  (`ReleasePrepTeam`), `agents/state/store.py` (`AgentStateStore`).
- First consumer: `pipeline/orchestrator.py::_run_quality_gate`
  (post-#1094 real-review gate).
- `.claude/rules/attune/xml-enhanced-prompts.md` — the implementation
  tasks (design phase) use XML-enhanced prompts.
