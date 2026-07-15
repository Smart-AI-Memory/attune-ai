# D-or-worse block triage — 2026-07-14

**Status: COMPLETE (2026-07-15).** All 12 REFACTOR blocks are cut
and merged; both verified deletions landed. The ratchet ledger on
`origin/main` holds exactly the 13 deliberate ACCEPT entries below —
the paydown plan's own definition of done. See "Paydown plan of
record" for the closing PR list.

Phase 0.5 of the paydown plan in
[library-health-2026-07-14.md](library-health-2026-07-14.md).
Subagent inventory (fan-in / 120-day churn / tests per block) with
the three DELETE chains re-verified centrally. The ratchet
(#1377) freezes this set; entries leave the allowlist as batches
land. Patrick approved Batch 1 + the two verified deletions
(2026-07-14).

## REFACTOR (12) — ALL CUT ✅

| Batch | Block | Grade → | PR |
|-------|-------|---------|----|
| 1 | `elicitation/bridge.py::form_from_dict` | F87→C15 | #1380 |
| 1 | `elicitation/widget.py::_control_html` | F84→A3 | #1380 |
| 1 | `elicitation/bridge.py::_validate_answer` | D22→A1 | #1380 |
| 2 | `mcp/workflow_handlers.py::_workflow_response` | D26→A4 | #1386 |
| 2 | `ops/runner.py::RunnerService._validate_recommendation` | D24→B9 | #1386 |
| 2 | `cli_commands/workflow_commands.py::cmd_workflow_run` | D21→B8 | #1386 |
| 3 | `project_index/dependency_analysis.py::_build_summary` | F48→A1 | #1389 |
| 3 | `workflows/document_gen/report_formatter.py::format_doc_gen_report` | D29→A3 | #1389 |
| 3 | `voice/formatter.py::_extract_from_workflow_result` | D23→C13 | #1389 |
| 4 | `workflows/rag_code_gen.py::RagCodeGenWorkflow.execute` | D24→below D | #1391 |
| 4 | `workflows/documentation_orchestrator.py::DocumentationOrchestrator.execute` | D22→below D | #1391 |
| 4 | `models/empathy_executor.py::EmpathyLLMExecutor.run` | D22→below D | #1391 |

(Batch 3 was completed twice in parallel by two independent
sessions — #1389 merged first; the duplicate, #1388, was closed as
superseded, same targets and grades.)

## ACCEPT (13) — live, stable, tested; refactoring is gold-plating

(+1 on 2026-07-15: `refresh_incremental` promoted from DELETE-hold —
see item 3 below.)

`format_secure_release_report` D28 (1 contained caller, 0 churn),
`HelpMaintenanceWorkflow.execute` D25, `TestMaintenanceWorkflow.
_generate_plan` D24 (registry-dispatched, tested),
`meta_workflows/.../run_workflow` D24 (stable since v4-era),
`sweep_to_board_html` D23 (young, watch), `_apply_custom_filters`
D23, `BackendInitMixin._initialize_backends` D22 (dedicated branch
tests), `_section_html` D22, `python_refs.py::check` D22,
`AuditQueryMixin` D22 + `.query` D21, `derive_lifecycle` D21
(young module, 0 churn since creation). These stay on the ratchet
allowlist deliberately — complexity is a tax paid on change, and
these aren't changing.

## DELETE-CANDIDATE (3) — verified chains

1. **`workflow_ship.py::ship_workflow`** (D27) — VERIFIED, and
   deeper than one function: the top-level `workflow_commands.py`
   facade importing it has ZERO callers itself; the live CLI uses
   `cli_commands/workflow_commands.py` (same name, different
   module — the release-prep two-implementations trap); the NL
   "ship" intent routes to `("release","prep")`. BUT `cmd_ship` is
   in `workflows/__init__.__all__` — public API. Removal = the
   whole legacy one-command family (morning/ship/fix-all/learn +
   facade) through the removing-dead-code gate with a deprecation
   path. Approved 2026-07-14, gated PR.
2. **`workflows/bug_predict_report.py::format_bug_predict_report`**
   (D23) — VERIFIED: only reference is a lint-suppressed re-export
   in `bug_predict.py`; the registered workflow never calls it.
   Approved 2026-07-14, gated PR.
3. **`project_index/index.py::ProjectIndex.refresh_incremental`**
   (D21) — WEAKEST: test-only usage, but a documented public method
   (possibly forward-looking watch-mode API). NOT approved — hold
   for a should-this-exist decision when project_index is next
   touched.
   **DECIDED 2026-07-15 (batch 3, Patrick): reclassified as ACCEPT.**
   Re-verified: zero production callers (both ProjectIndex consumers
   use full `refresh()`), but it is a tested, documented public
   method on a published package with ~zero churn since v4.8.0 and
   no watch-mode subsystem yet. Fits the ACCEPT rationale (complexity
   is a tax on change; it isn't changing). Allowlist entry stays,
   ACCEPT count 12 → 13.

## Paydown plan of record (Patrick-approved 2026-07-14 evening)

Definition of done: the ratchet ledger contains ONLY deliberate
ACCEPT entries, each justified above — not zero. **Met 2026-07-15:**
the ledger holds exactly the 13 ACCEPT entries above, zero REFACTOR
blocks remaining.

Method per batch: pin-then-cut (pins PR merges before cuts PR),
serial-suite verification at the orchestrator's gate, ratchet
entries deleted in each cut PR. One batch per session; freeze-
compatible.

- **Batch 1 — elicitation** (2026-07-14, 2 PRs): pins #1378, cuts
  #1380. `form_from_dict` F87→C15, `_control_html` F84→A3,
  `_validate_answer` D22→A1.
- **Deletions** (2026-07-14/15, 1 PR): #1381 removed the legacy
  one-command family (`ship_workflow` D27 + facade) and the
  orphaned `format_bug_predict_report` D23, both deprecation-first.
- **Batch 2 — churn-hot infra** (2026-07-15, 3 PRs): #1383 (the
  standalone `cmd_workflow_run` exit-0-on-failure fix, shipped
  decoupled from the behavior-preserving cut), pins #1384, cuts
  #1386. `_workflow_response` D26→A4,
  `RunnerService._validate_recommendation` D24→B9,
  `cmd_workflow_run` D21→B8.
- **Batch 3 — formatters + the last F** (2026-07-15, 2 PRs): pins
  #1387, cuts #1389 (completed independently in parallel by two
  sessions — see the REFACTOR table note above).
  `format_doc_gen_report` D29→A3, `_build_summary` F48→A1,
  `_extract_from_workflow_result` D23→C13. Also closed the held
  `refresh_incremental` should-this-exist decision: reclassified
  ACCEPT (zero production callers, but tested/documented/stable —
  see DELETE-CANDIDATE item 3).
- **Batch 4 — workflow executes** (2026-07-15, 1 PR): #1391
  (pins + cuts combined). Opening subsystem-value-gate check
  confirmed `EmpathyLLMExecutor` is alive and central
  (`ExecutorMixin` is mixed into every LLM-backed workflow via
  `BaseWorkflow`) — refactored, not deleted. `RagCodeGenWorkflow.
  execute` D24, `DocumentationOrchestrator.execute` D22,
  `EmpathyLLMExecutor.run` D22 — all cut below D.

Post-freeze checkpoint (still open): re-check the 13 ACCEPT
rationales against fresh churn data once — an ACCEPT that starts
churning is promoted to REFACTOR.

Trajectory (actual): 27 D-or-worse blocks at ratchet ship (2026-07-14)
→ 13 ACCEPT-only entries on `origin/main` (2026-07-15, verified
against the live ratchet allowlist), across batches 1-4 plus the
two deletions above. Done.
