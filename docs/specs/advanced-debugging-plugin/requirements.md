# Advanced Debugging Plugin — Requirements

**Status: requirements chair-ruled per item** — authored by the
round table (thread `producing-advanced-debugging-plugin-001`); compiled deterministically by
`attune.roundtable.compiler` (V2-P2). Approved items only;
declined: none;
unruled: none.

All eight items chair-approved 2026-07-19. RR-7 carries the panel's 2-1 binding (manual-only triage in v1). RR-8 approved over the TR-6 staging cap. Run was DEGRADED: claude critic seat absent (401), one LINT_DIRTY round-3 citation gate trip — receipts in decisions.md.

## Requirements

**RR-1 — Persist first-class DiagnosisRecords**
Define a versioned `DiagnosisRecord` in `src/attune/models/telemetry/data_models.py`, persisted at `~/.attune/telemetry/diagnosis_records.jsonl` beside—but separate from—the workflow-run corpus.
- Each record identifies its source `WorkflowRunRecord` and captures symptom, evidence chain, root-cause hypothesis, confidence, proposed fix, verification receipt, status, timestamps, and schema version.
- Records are append-safe, reloadable, and minable without modifying `~/.attune/telemetry/workflow_runs.jsonl`.
- Malformed, fixture-derived, and pre-cutover records are rejected or excluded using explicit purity rules comparable to `src/attune/pipeline_learner/corpus.py`.
- A live-fire test persists and reloads a `DiagnosisRecord` for a real failed corpus run without losing provenance.
(table: untagged; chair: approved)

**RR-2 — Stamp and isolate diagnostic runs**
Diagnostic workflows must enter the standard telemetry path under a distinct `attune-heal` trigger while remaining excluded from diagnosis mining and learning inputs.
- `attune-heal` is accepted by the trigger contract in `src/attune/models/telemetry/run_context.py` and the route validation in `src/attune/ops/routes/runner.py`.
- `src/attune/workflows/telemetry_mixin.py` emits diagnostic runs through the same workflow telemetry lifecycle and schema as other runs, differing only in trigger and diagnostic metadata.
- Pipeline-learner weighting in `src/attune/pipeline_learner/mining.py` does not classify `attune-heal` runs as manual activity.
- Failed-run selection, headless triage, and lesson graduation exclude all `attune-heal` runs.
- An integration receipt demonstrates emission of an `attune-heal` run and its omission from a subsequent mining pass.
(table: untagged; chair: approved)

**RR-3 — Provide on-demand diagnosis from the run view**
The v1 entry point must be an explicit “Why did this fail?” action for failed attune runs, preserving chair control over LLM spend.
- `src/attune/ops/static/js/run_view.js` exposes the action only for eligible failed runs and displays pending, completed, failed, and unavailable states using existing conventions.
- `src/attune/ops/routes/runner.py` owns the on-demand diagnosis endpoint, accepts a run identifier, validates that the source run exists and failed, and dispatches exactly one traceable diagnostic run.
- Repeated requests are idempotent or visibly linked to prior `DiagnosisRecord` entries rather than silently duplicating spend.
- No diagnosis starts automatically from run ingestion or page load in v1.
- An integration receipt exercises the run-view request through the endpoint and links the returned diagnostic run to its source failure.
(table: untagged; chair: approved)

**RR-4 — Recall lessons before gathering evidence**
Diagnosis must query `idx:attune_memory` before evidence gathering so verified historical lessons act as diagnostic priors rather than post-hoc decoration.
- Each diagnostic attempt records whether `FT.SEARCH` or `FCALL recall_digest` was used, the returned lesson references, and any degraded-mode reason.
- Recalled lessons inform candidate hypotheses, but the `DiagnosisRecord` distinguishes recalled priors from evidence observed in the failed run.
- Redis unavailability degrades to an explicit no-priors state and does not prevent diagnosis.
- A receipt shows a known lesson influencing a hypothesis while unsupported recalled claims are not promoted to evidence.
(table: untagged; chair: approved)

**RR-5 — Convene a receipted diagnosis panel**
Use the shipped round-table machinery in `src/attune/roundtable/producing.py` to generate independent root-cause hypotheses and a moderator synthesis with visible uncertainty and dissent.
- At least two independent diagnosis seats inspect the same bounded evidence pack before seeing one another’s hypotheses.
- The moderator produces a ranked synthesis containing supporting evidence, contradictory evidence, confidence, and unresolved dissent.
- Seat identities and rotation-ledger participation are retained in the `DiagnosisRecord`.
- Panel execution maps failures onto the existing `producing.py` failure taxonomy and respects its R5 cap of 10 rather than retrying indefinitely.
- A receipt covers successful synthesis, retained dissent, and at least one classified panel-failure path.
(table: untagged; chair: approved)

**RR-6 — Propose and verify fixes without applying them**
For sufficiently supported diagnoses, use the seams in `src/attune/roundtable/solutions.py` to propose fixes, materialize them only in scratch worktrees, validate them, review their diffs, and discard them after reporting.
- The implementation binds to the existing materialize, validate, diff, review, and discard lifecycle rather than creating a parallel execution mechanism.
- No proposed change is applied to the user’s working tree, committed, pushed, or merged by the v1 plugin.
- Every proposal includes its diff, validation commands, command results, reviewer verdict, residual risks, and disposition.
- The reviewing seat differs from the proposing seat, and failed validation remains visible rather than being summarized as a successful fix.
- A live-fire receipt demonstrates scratch-worktree materialization, a relevant check, different-seat review, and discard while the original worktree remains unchanged.
(table: untagged; chair: approved)

**RR-7 — Support opt-in failed-run triage and lesson graduation**
Beyond the primary on-demand action, v1 may process failed attune runs through an explicitly invoked headless triage routine integrated with `src/attune/roundtable/routine.py`.
- The routine follows the existing `clean-run` execution pattern: a bounded failed-run battery, seat deliberation, and a digest linking every conclusion to its `DiagnosisRecord`.
- The digest groups repeated symptoms or root-cause hypotheses without merging conflicting evidence or concealing dissent.
- Graduation requires a successful verification receipt and explicit chair approval; unverified, rejected, and `attune-heal` diagnoses never become lessons.
- V1 exposes triage through a manual command only; scheduler integration is deferred.
- A routine receipt shows eligible failures included, self-records excluded, and no automatic promotion at R8 or any other stage.
(table: untagged; chair: approved)

**RR-8 — Expose diagnoses through the curator grounding seam**
Provide a read-only curator source under `src/attune/curator/sources/` so downstream reporting can consume eligible `DiagnosisRecord` entries without reading raw persistence files directly.
- The source uses the canonical `DiagnosisRecord` loader and applies the same malformed-record, fixture, cutover, and `attune-heal` exclusion rules as diagnosis mining.
- Curator output preserves source-run provenance, diagnosis status, confidence, verification state, lesson references, and unresolved dissent.
- Proposed diffs and potentially sensitive evidence are excluded or redacted unless explicitly requested through an authorized detailed view.
- A source-level integration receipt loads persisted diagnoses, excludes ineligible records, and produces deterministic grounding documents for downstream reporting.
(table: untagged; chair: approved)
