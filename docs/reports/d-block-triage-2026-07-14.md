# D-or-worse block triage — 2026-07-14

Phase 0.5 of the paydown plan in
[library-health-2026-07-14.md](library-health-2026-07-14.md).
Subagent inventory (fan-in / 120-day churn / tests per block) with
the three DELETE chains re-verified centrally. The ratchet
(#1377) freezes this set; entries leave the allowlist as batches
land. Patrick approved Batch 1 + the two verified deletions
(2026-07-14).

## REFACTOR (12) — live and churning, or high blast radius

| Batch | Block | Grade | Driver |
|-------|-------|-------|--------|
| 1 | `elicitation/bridge.py::form_from_dict` | F87 | 4 MCP call sites + recall_digest; hot file |
| 1 | `elicitation/widget.py::_control_html` | F84 | live render path, churning |
| 1 | `elicitation/bridge.py::_validate_answer` | D22 | every form response flows through it |
| 2 | `mcp/workflow_handlers.py::_workflow_response` | D26 | 6 call sites, 11 changes/120d, prior swallowed-error bug (#1173) |
| 2 | `ops/runner.py::RunnerService._validate_recommendation` | D24 | hottest file in set (15 changes/120d), stdout loop |
| 2 | `cli_commands/workflow_commands.py::cmd_workflow_run` | D21 | `attune workflow run` entry, 12 changes/120d; fold the exit-0-on-failure fix in |
| 3 | `project_index/dependency_analysis.py::_build_summary` | F48 | 3 independent production entry points |
| 3 | `workflows/document_gen/report_formatter.py::format_doc_gen_report` | D29 | 3 call sites depend on exact output shape |
| 3 | `voice/formatter.py::_extract_from_workflow_result` | D23 | self-declared primary output API |
| 4 | `workflows/rag_code_gen.py::RagCodeGenWorkflow.execute` | D24 | registered workflow, 13 changes/120d |
| 4 | `workflows/documentation_orchestrator.py::DocumentationOrchestrator.execute` | D22 | 2 live integration points, prior #685 bug |
| 4 | `models/empathy_executor.py::EmpathyLLMExecutor.run` | D22 | ALIVE (3 subsystems) — doc-fiction lesson confirmed again |

## ACCEPT (12) — live, stable, tested; refactoring is gold-plating

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

## Paydown plan of record (Patrick-approved 2026-07-14 evening)

Definition of done: the ratchet ledger contains ONLY deliberate
ACCEPT entries, each justified above — not zero. Expected floor
after the in-flight work (batch-1 cuts −3, deletions −2): 22, of
which 9 are the remaining REFACTOR blocks.

Method per batch: pin-then-cut (pins PR merges before cuts PR),
serial-suite verification at the orchestrator's gate, ratchet
entries deleted in each cut PR. One batch per session; freeze-
compatible.

- **Batch 2 — churn-hot infra** (1 session, 3 PRs; amended
  2026-07-14): FIRST a standalone small PR fixing the known
  `cmd_workflow_run` exit-0-on-failure bug (own regression test —
  a deliberate behavior change must not ride inside a
  pins-prove-preservation cut; and the bug is live today, so it
  ships sooner decoupled). THEN pins + cuts as usual for
  `_workflow_response` D26 (pin the MCP response shapes — the
  exact-dict-equality trap lives here),
  `RunnerService._validate_recommendation` D24 (stdout-loop
  states), and `cmd_workflow_run` D21 — now purely
  behavior-preserving like every other cut.
- **Batch 3 — formatters + the last F** (1 session, 2 PRs):
  `format_doc_gen_report` D29, `_extract_from_workflow_result`
  D23, `_section_html` D22, `_build_summary` F48 (highest care).
  Parallel pin agents (similar section-builder shapes), one cut
  pass. Natural moment for the held `refresh_incremental`
  should-this-exist decision (sibling file).
- **Batch 4 — workflow executes** (1 session, 3 small PRs):
  `RagCodeGenWorkflow.execute` D24,
  `DocumentationOrchestrator.execute` D22,
  `EmpathyLLMExecutor.run` D22. Stage-extraction, mock-based
  pins, plus one dogfood-run receipt per cut (registered ≠
  working — these wrap LLM/SDK calls). OPENING STEP (amended
  2026-07-14): a 15-minute subsystem-value-gate check on
  `EmpathyLLMExecutor`'s callers (`escalation/chain`,
  `escalation/evaluator`, `executor_mixin`) BEFORE any pin work —
  it is the live executor of a framework whose core was deleted
  in 9.0.0; if its callers are themselves retirement candidates,
  the right move is deletion-with-deprecation (ledger −1 free),
  not a careful refactor of dead-subsystem plumbing. Proceed with
  the refactor only if the check says the callers stay.

Post-freeze checkpoint: re-check the 12 ACCEPT rationales against
fresh churn data once — an ACCEPT that starts churning is promoted
to REFACTOR.

Trajectory: 27 → 22 (in flight) → ~13 (batches 2+3) → 12
all-ACCEPT (batch 4).
