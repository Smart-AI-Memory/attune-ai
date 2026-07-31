# Phase 0 — Seam inventory and characterization proof

**Status:** executed 2026-07-30 (Task 0, chair-authorized).
Rows naming a TODAY-existing interface are mechanically checked
by the dry-trace section of
`tests/unit/characterization/test_outcome_first_phase0.py` — a
checked row whose interface stops importing fails CI. Rows
marked **†** are design commitments (a Phase 1/2 deliverable or
an out-of-repo surface) — they name where the concept WILL
land, and the corresponding phase's tests must convert them to
checked rows when that phase executes.

## Seam map: ruling concept → existing interface

| Ruling concept | Existing interface | Notes |
| --- | --- | --- |
| Explicit entry (`attune fix`) † | new subparser in `src/attune/cli_minimal.py` (Phase 1) | namespace verified free; sibling of `workflow`/`diagnose` |
| Outcome contract DTO † | internal dataclass translated ONCE into `execute(**input_data)` kwargs via `cmd_workflow_run`'s input path | boundary object, never a public schema (gate 2) |
| Workflow selection | `attune.workflows.get_workflow` / `list_workflows` (`WORKFLOW_REGISTRY`) | no second registry |
| Execution | `attune.cli_commands._exit_codes.run_workflow_with_exit_code` | owns the 0/1/2/3 exit contract |
| Receipt evidence | `WorkflowResult` fields (`success`, `stages`, `final_output`, `cost_report`, `metadata`, `summary`, `suggestions`, `error`, `error_type`, `transient`) | receipt PROJECTS these; probes evaluated test-side |
| Verification probes † | real `pytest` subprocess against the scenario copy (Phase 2) | independent of workflow exit; fixture boundary already proven |
| Routing (deferred NL) | `attune.cli_router.HybridRouter.route` / `attune.routing.SmartRouter.route_sync` | Phase 4 gate; see keyless probe below |
| `--explain` projection | `attune.routing.RoutingDecision` (checked) + `workflow_cls.input_schema` † (conditional attr, Phase 1 pins it per selected workflow) | existing data only |
| Run history / diagnosis | `attune.diagnosis.engine.diagnose` + canonical run stream | `attune diagnose` already consumes it |
| Confirmation gates | `_auth_preflight` (checked) + spend gate inline in `cmd_workflow_run` | reuse, not reinvent |
| Cost/telemetry | `attune.telemetry.usage_tracker.UsageTracker` | no second telemetry system |
| Help/docs surface † | author-feature projector pipeline (out-of-repo: attune-author) | projector-owned, never hand-edited; Phase 3 adds drift guards |

## REMOVED (concepts with no interface — by design)

Parallel planner; second workflow registry; separate executor;
evidence store; new orchestration layer; second telemetry system;
new execution lifecycle; second source of truth. Each was mapped
to "existing interface already owns this" above; none survives as
a new component. (Ruling: "map every proposed concept to an
existing interface or remove it.")

## Evidence: the exit-code premise, corrected against the code

The roundtable (and spec H2) cited the lessons-corpus finding
that `attune workflow run` exits 0 while the workflow errored.
Phase 0 verified the CURRENT tree: that divergence was **fixed**
by the workflow-failure-exit-propagation spec —
`_exit_codes.py` now maps success→0, planned failure→1, uncaught
exception→2, CLI error→3, and the characterization tests pin all
four. One residual, documented as INTENTIONAL backwards
compatibility: a legacy result with NO `success` attribute maps
to exit 0. So H2's principle stands on a narrower base: exit
code alone still cannot prove a done condition (legacy loophole
+ probes are simply out of the exit code's scope), but the
receipt design builds on a sound 0/1/2/3 floor, not on the old
bug.

## Evidence: keyless routing of fix requests (live probe)

`HybridRouter.route("fix the failing test in my project")`,
keyless: returns `bug-predict` at confidence 0.17 via keyword
fallback — a concrete workflow, confidently, with **no
abstention path**, and no `fix` keyword exists in the builtin
map. This is the false-confident-route gap Phase 4 closes,
pinned INCIDENTAL so its closure is a deliberate diff.

## Canonical scenario walkthrough (traced, then dry-checked)

`tests/fixtures/outcome_first_fix/` seeds an off-by-one in
`pricing.py` (`>` vs `>=` at the bulk boundary). Trace: contract
DTO {goal: boundary order is bulk; done: target test passes +
suite green + diff confined to `pricing.py`; probes: pytest
subprocess} → `get_workflow` selects the fix-capable workflow →
`run_workflow_with_exit_code` executes → receipt projects
`WorkflowResult` + test-side probe results. Live boundary
verified today: explicit run = 1 failed (target) / 5 passed;
main-suite discovery collects nothing (exit 5), so the seeded
failure can never leak into CI.

**Phase 0 acceptance: MET** — the scenario traces through
existing interfaces only; every mapped interface import- and
signature-checked; no changes under `src/attune/`.
