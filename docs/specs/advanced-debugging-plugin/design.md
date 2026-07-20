# Advanced Debugging Plugin — Design

**Status:** draft for chair review (2026-07-19). Requirements
chair-ruled per item (RR-1..RR-8, thread
`producing-advanced-debugging-plugin-001`); this design binds each
requirement to concrete seams and names the build phases.

## Design stance

Reuse over invention, three ways:

1. **A diagnosis IS a dashboard run.** The on-demand entry point
   spawns `attune diagnose <run_id>` through the existing
   `RunnerService` with `ATTUNE_RUN_TRIGGER=attune-heal`. That one
   choice buys SSE streaming, the busy-lock, the run view, run
   persistence, AND RR-2's corpus stamping with zero new runner
   machinery — the diagnostic run is just another run.
2. **The panel and fix loop are the shipped roundtable seams**
   (`Board`, `producing` failure taxonomy, `solutions`
   materialize/validate/review/discard) — no parallel executor.
3. **The store is the telemetry layer's third file.**
   `TelemetryStore` grows `diagnoses_file` beside
   `workflow_runs.jsonl`, inheriting home-global resolution,
   suite isolation (RC-4 fixture), and no-delete rotation.

## Components

### 1. Schema + store (RR-1)

- `DiagnosisRecord` in `src/attune/models/telemetry/data_models.py`
  (`schema_version: 1`): `diagnosis_id`, `source_run_id`,
  `workflow_name`, `created_at`, `status`
  (`open | fix-proposed | verified | rejected | graduated`),
  `priors` (lesson refs + degraded-mode reason), `evidence`
  (typed entries: kind, source, content-digest — priors and
  observed evidence are distinct kinds per RR-4), `hypotheses`
  (statement, rank, confidence, supporting/contradicting evidence
  refs), `synthesis`, `dissent`, `panel` (seat ids, absences,
  failure codes), `proposed_fix`
  (diff digest, checks + results, reviewer seat, verdict,
  disposition), and `config_used`
  (confidence scale + fix threshold — the dissent register's
  exposure requirement).
- Persisted at `~/.attune/telemetry/diagnosis_records.jsonl` via
  `TelemetryStore.log_diagnosis`; loader
  `src/attune/diagnosis/store.py` applies purity rules mirroring
  `pipeline_learner/corpus.py` (fixture-name exclusion, cutover
  pin at this spec's ship date, malformed-line skip counters).

### 2. Trigger extension (RR-2)

- `attune-heal` joins `_VALID_TRIGGERS` in
  `src/attune/models/telemetry/run_context.py` and the ops route
  validator. Only the diagnosis engine sets it (via the runner's
  existing trigger threading — the RC-3 seam, unchanged).
- `pipeline_learner/mining.py` counts `attune-heal` as non-manual;
  `pipeline_learner/corpus.py` excludes it from eligible records.
  Triage selection (component 6) and graduation exclude it too —
  no diagnose-the-diagnosis loops by default.

### 3. Diagnosis engine (`src/attune/diagnosis/`)

New package; CLI `attune diagnose <run_id>` (manual-first, and
what the dashboard spawns).

Pipeline (each stage writes into the record as it goes):

1. **Load** the source `WorkflowRunRecord` (+ ops run record's log
   tail when one exists) — refuse non-failed or `attune-heal`
   sources.
2. **Priors** (RR-4): query `idx:attune_memory`
   (`FCALL recall_digest` with error-shape terms, OR-joined);
   Redis-down → explicit `priors_degraded` reason, never a block.
3. **Evidence pack** (`evidence.py`): bounded-bytes packet — run
   record fields, log tail, source excerpts for files named in the
   error, recent `git log --oneline` context. Deterministic
   assembly, size cap in config.
4. **Panel** (RR-5, `panel.py`): ≥2 seats invoked independently
   with the same pack (R1 text-only), moderator synthesis with
   ranked hypotheses + retained dissent; failures map onto
   `producing.FAILURE_CODES`; R5 cap 10 invocations; absent seats
   degrade the panel, never block it (observed live: the claude
   seat 401'd during this spec's own authoring).
5. **Fix proposal** (RR-6, gated): only when top confidence ≥ the
   exposed threshold. Binds `solutions.materialize` (scratch
   worktree) → `solutions.validate` (named checks, exact-tail
   receipts) → different-seat review → `solutions.discard`.
   Everything lands in `proposed_fix`; the user's tree is never
   touched; failed validation stays visible (TAC-4).

### 4. On-demand surface (RR-3)

- `POST /runs/{run_id}/diagnose` in `src/attune/ops/routes/`
  (client-token + `allow_run` gates): validates the source run
  exists and failed, checks the diagnosis store for an existing
  record for that `source_run_id` (idempotency — returns the link
  instead of double-spending), then dispatches ONE runner
  subprocess: `attune diagnose <run_id>` with trigger
  `attune-heal`.
- `run_view.js`: "Why did this fail?" button rendered only on
  terminal-failed runs; navigates to the diagnostic run's own view
  (streaming for free); a diagnosis chip links completed
  diagnoses back to their source run. No auto-start anywhere.

### 5. Lesson graduation interface (dissent-bound)

- `graduation.py` defines a `LessonPublisher` protocol; v1 ships
  only a render-for-chair implementation reusing the roundtable
  `LessonCandidate` lint (receipt-or-waiver gate). Publication
  target (`.claude/lessons.md` direct vs. projected source) stays
  behind the interface until the chair rules — no direct corpus
  writes in v1.

### 6. Triage routine (RR-7)

- Registered beside `clean-run` in
  `src/attune/roundtable/routine.py` as `failed-run-triage`:
  select the last N non-`attune-heal` failed runs since the prior
  digest, run the engine per failure (bounded), cluster repeated
  root-cause hypotheses, digest thread
  `routine-failed-run-triage-<date>` — R8 absolute, manual
  invocation only in v1 (the 2-1 binding).

### 7. Curator source (RR-8)

- `src/attune/curator/sources/diagnoses.py`: read-only over the
  canonical loader, same exclusion rules as mining; emits
  provenance, status, confidence, verification state, lesson refs,
  dissent. Diffs and raw evidence redacted unless the detailed
  view is explicitly requested.

## Configuration

`DiagnosisConfig` (env-overridable, defaults conservative):
`confidence_scale` (three-level: low/medium/high),
`fix_proposal_threshold` (default: high), `panel_seats` (default
2), `evidence_budget_bytes` (default 64 KB), `triage_batch_max`
(default 5). Every record stamps `config_used` — policy is data,
never hard-code.

## Build phases

- **A — substrate:** RR-1 schema/store + RR-2 trigger extension.
  Pure model/telemetry layer; unit + live-fire persist/reload.
- **B — engine core:** load → priors → evidence → panel; CLI
  `attune diagnose`; DiagnosisRecord written end-to-end (RR-4,
  RR-5).
- **C — surface:** endpoint + run-view button + chip (RR-3).
- **D — loops:** fix proposal (RR-6), triage routine (RR-7),
  curator source (RR-8), graduation interface.

Each phase lands as its own PR with the RR acceptance receipts it
covers; Phase B's canonical receipt is a live diagnosis of a real
failed run from the corpus.

## Risks

- **Spend:** a panel diagnosis is multiple CLI invocations —
  bounded by caps, on-demand-only, and the R5 ceiling; the triage
  batch max bounds the routine.
- **Evidence vs. context limits:** the byte budget truncates
  deterministically (largest-value-first ordering: error, log
  tail, source excerpts).
- **Seat auth fragility:** absent-seat degradation is first-class
  in the record (`panel.absences`), proven necessary by this
  spec's own authoring run.
- **Store growth:** same 50 MB rotate-to-archive policy as the run
  corpus.
