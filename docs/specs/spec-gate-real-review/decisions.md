# Decisions — spec-gate-real-review

**Created:** 2026-06-25

---

## D1 — The `/spec` quality gate is a live bug, not just dead code

Investigation (2026-06-25) confirmed the gate path is **structurally
reachable from the live `/spec` entrypoint** and **functionally a
no-op**:

- `spec/runner.py::execute_with_approval(skip_gates=False)` is the
  default; it constructs `PipelineOrchestrator(skip_gates=False)`.
- `run_all -> run_gates_for_task -> _run_quality_gate` runs by default.
- `_run_quality_gate` builds a `code_reviewer + security_auditor` team
  via `DynamicTeamBuilder.build_from_plan`, which instantiates
  `StubAgent` (the only agent type the builder produces).
- `StubAgent.process()` returns `SDKAgentResult(success=True, cost=0)`
  — fake pass, no review.

**Decision:** treat this as a live-feature bug. The fix is to rewire
`_run_quality_gate` to call the real `CodeReviewWorkflow` +
`SecurityAuditWorkflow` directly and gate on their actual scores. The
dead team engine is then removed as the now-orphaned consumer.

---

## D2 — Corrected dead/live classification (premise correction)

The Phase B handoff's "dead engine" target list was partly **wrong**.
Grepping live callers (not just imports) gives the real split. This
table is the auditable record; removal follows it exactly.

### KEEP LIVE — do NOT delete

| Symbol / module | Why it is live |
|---|---|
| `pipeline/orchestrator.py` `PipelineOrchestrator` | The `/spec` engine. Used by `spec/runner.py`, the `/spec` command, ~30 help docs. Only its `_run_quality_gate` *backend* is fake. |
| `orchestration/execution_strategies.py` + `_strategies/` (`ParallelStrategy`, `StrategyResult`, `get_strategy`, ABC, all concrete strategies) | `OrchestratedHealthCheckWorkflow` (registered `health-check` / `orchestrated-health-check`) does `ParallelStrategy().execute(...)`. |
| `workflows/progressive/orchestrator.py` `MetaOrchestrator` | **Name collision** with the dead orchestration `MetaOrchestrator`. The progressive one is live tier-escalation logic used by `ProgressiveWorkflow`. |
| `orchestration/agent_templates/` (`get_template`, `get_all_templates`, `AgentTemplate`, ...) | Used as prompt/routing DATA in `meta_workflows`, `prompts`, `routing`, `test_generator`. Data, not run-path. |
| `TaskDecomposer._parse_tasks_from_xml` (`wizards/decomposer.py`) | Live via `pipeline/spec_reader.py` (parser-only, `workflow=None`). |
| `verification/strategies.py::get_strategy` | Unrelated to orchestration (a false grep hit). |

### DEAD — remove

| Symbol / module | Dormancy evidence |
|---|---|
| `orchestration/agent_models.py::StubAgent` | Only consumers: `team_builder` (dead) + tests + the fake gate. |
| `orchestration/dynamic_team.py` (`DynamicTeam`, `DynamicTeamResult`) | Only built by `team_builder` / `workflow_composer` (both dead) + the fake gate. |
| `orchestration/team_builder.py` (`DynamicTeamBuilder`, `TeamSpecification`) | Callers: fake gate (rewired away), dead `multi_agent_mixin`, `meta_orchestrator`. |
| `orchestration/workflow_composer.py` (`WorkflowComposer`) | No live caller; only referenced from the dead path. |
| `orchestration/workflow_agent_adapter.py` (`WorkflowAgentAdapter`) | No live caller. |
| `orchestration/meta_orchestrator.py` + `meta_orch_*` helpers (the orchestration `MetaOrchestrator`, distinct from progressive) | No caller outside `orchestration/` + its own tests. |
| `orchestration/team_store.py` (`TeamStore`) | Only feeds `DynamicTeamBuilder`. (Verify at removal time.) |
| `workflows/multi_agent_mixin.py` (`MultiAgentMixin`) | **Zero** workflow subclasses it. |
| `workflows/base.py` multi-agent params (`multi_agent_configs`, Phase-4 DynamicTeam wiring) | Only fed the dead mixin path. |
| `wizards/decomposer.py::TaskDecomposer.decompose()` LLM path (`_call_llm(prompt, tier, label)` signature-drift bug) | Dead LLM half; keep the live parser half. |
| `wizards/internal_workflow.py` (same `_call_llm` drift) | Verify caller at removal time. |

---

## D3 — Gate rewire shape

`_run_quality_gate` will instantiate `CodeReviewWorkflow` and
`SecurityAuditWorkflow` directly (not via a team), run them on the
task's target files (parallel via `asyncio.gather`), extract real
scores, and apply the existing 70.0 thresholds. On a review-workflow
exception the gate **fails closed** (returns not-passed), never
fake-passes. This removes the last dependency on the dead engine.

Open question for implementation: reuse the existing `quality_gates`
threshold dict shape, or simplify now that there is no team plan.
Resolve in the impl task; default to the simpler direct-score check.

---

## D4 — Process

- Tag pre-removal state (`archive/spec-gate-real-review-pre-removal`)
  before deleting, per removing-dead-code.md.
- Breaking removal of public `attune.orchestration` symbols -> version
  bump + CHANGELOG `release-notes` concern.
- Dogfood receipt required for R1/R2 (a real bad-task gate failure),
  per the "registered != working" lesson — mocked tests alone do not
  close this.

---

## D-FINAL — Engine removed; task 4 premise was wrong (deferred)

**Shipped (2026-06-26 session):**

- Tagged `archive/spec-gate-real-review-pre-removal` before deletion.
- Removed the dead engine (tasks 2 + 3): deleted `agent_models.py`
  (`StubAgent` — entire file; every consumer of its `AgentLike` /
  `SDKAgentResult` / `SDKExecutionMode` / `QualityGate` symbols lived in
  the dead chain or in dead tests, no live `src/` consumer),
  `dynamic_team.py`, `team_builder.py`, `workflow_composer.py`,
  `workflow_agent_adapter.py`, `meta_orchestrator.py` + the three
  `meta_orch_*` mixins (they die together — `meta_orchestrator` imported
  them), `team_store.py`, and `workflows/multi_agent_mixin.py`. Pruned
  `orchestration/__init__.py` to agent-templates + execution-strategies
  only. Removed `BaseWorkflow`'s `multi_agent_configs` param + the
  `MultiAgentStageMixin` base. Deleted 11 dead test files; trimmed the
  dead orchestration-pipeline classes from
  `test_critical_workflows_smoke.py` and the `WorkflowComposer` class
  from `test_post_simplification.py`; updated the
  `test_registry_coverage.py` note.
- **Regression proof (R4):** the `health-check` workflow ran end-to-end
  through `ParallelStrategy().execute()` and returned a
  `HealthCheckReport` — the live strategies survived. R6 (`import
  attune.orchestration`) clean. 3,678 unit tests + the integration smoke
  suite green.
- `KEEP LIVE`, confirmed by re-grep: `execution_strategies` /
  `_strategies`, `agent_templates`, the progressive `MetaOrchestrator`,
  `PipelineOrchestrator`, and `TaskDecomposer._parse_tasks_from_xml`.

**Task 4 (decompose LLM path) — premise corrected, DEFERRED.** D2
classified `TaskDecomposer.decompose()`'s LLM path as "dead." That is
**wrong**: `decompose()` is reachable from `wizards/base.py`
(`_run_decompose_step`), and the `TASK_DECOMPOSE` step it serves is
declared by **5 live builtin wizards** (debug, release_prep, test_gen,
refactor, security). Its `_call_llm(prompt, ModelTier.CAPABLE,
"decompose")` call **is** signature-drifted against the real
`_call_llm(tier, system, user_message, …)` — so the path is
**broken-by-drift, not dead**. Deleting it would permanently remove a
feature 5 wizards declare, not clean up dead code. Correct fix is to
*repair* the arg order (or settle whether the wizard *run* engine is
itself live — this ties to the reversed
`interactive-orchestration-access` spec, #1093, which found the wizard
engine non-functional). Left untouched in this PR. Same applies to
`internal_workflow.py`: the `_call_llm` mention there is docstring-only;
`WizardInternalWorkflow` is the live wizard→workflow bridge — **no
change needed** (also a D2 over-broad listing).

**Docs (task 5) — DEFERRED.** ~16 prose doc files (user guides,
tutorials, the shipped `plugin/help/generated/*/orchestration.md`
corpus) still describe the removed engine. None break CI (no
`mkdocstrings :::` autogen targets the deleted modules; wiring audit =
0 findings; `mkdocs build --strict` unaffected). Rewriting them is a
separable docs effort — and regenerating the `.help` corpus triggers
the whole-feature LLM re-polish risk. Tracked as a follow-up; CHANGELOG
`### Removed (BREAKING)` entry added under `[Unreleased]`.
