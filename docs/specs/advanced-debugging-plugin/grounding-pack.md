# Grounding pack — advanced-debugging-plugin (producing-run input)

**Subject:** An advanced debugging plugin — the "diagnose" stage of
a self-healing loop for attune — that turns failed workflow runs
into first-class, minable DiagnosisRecords, uses the multi-LLM
round table as debugging staff, and proposes (never auto-applies)
fixes.
**Provenance:** chair-approved one-page treatment at
`docs/specs/advanced-debugging-plugin/treatment.md` (2026-07-19,
drafted from a live brainstorm; chair: Patrick). **Arming:**
per-spec (chair queued this pack with "proceed"; no standing
cadence).

## The frame the treatment fixed (seed, not contract)

- Self-healing loop = sense → diagnose → propose → verify → learn.
  Attune ships four stages; diagnose is the gap this plugin fills.
- Core artifact: **DiagnosisRecord** — symptom → evidence chain →
  root-cause hypothesis → confidence → proposed fix → verification
  receipt. Persisted beside the run corpus; minable; verified
  diagnoses graduate into lessons.
- Moat: **lessons as diagnostic priors** — recall the 727-lesson
  corpus (receipt-backed root-cause episodes for this codebase)
  BEFORE evidence gathering.
- LLM team roles (all machinery shipped): diagnosis panel
  (independent seat hypotheses → moderator synthesis, dissent
  recorded); fix loop with cross-seat review (solutions loop:
  text proposals → scratch-worktree materialize → receipted checks
  → different-seat review → chair); automated error-check routines
  on the clean-run pattern (headless battery → seats deliberate →
  digest; R8 never promotes).
- Use cases, nearest first: "Why did this fail?" button on the run
  view; nightly failed-run triage digest; automated error-check
  sweep; deepened test-failure debugging (v2); CI red-lane
  diagnosis (v2); runtime self-healing for arbitrary apps
  (horizon only).

## Chair rulings already made (constraints — conform, don't re-litigate)

1. **First target: attune's own failed runs** (dogfood-first).
2. **Propose-only v1** — the chair rules on every fix; auto-apply
   is a later rung behind its own gate.
3. **On-demand trigger first** — diagnosis is LLM spend; the
   button, then opt-in auto thresholds later.
4. **Self-records included but stamped** — diagnostic runs carry a
   new trigger class (`attune-heal`), enter the corpus, excluded
   from mining.

## Code reality (cite these seams; verify claims against them)

- Run corpus: `~/.attune/telemetry/workflow_runs.jsonl`;
  `WorkflowRunRecord` in
  `src/attune/models/telemetry/data_models.py` (has `trigger`,
  `project`, `sdk stage detail`, `success`, `error`).
- Trigger contract: `src/attune/models/telemetry/run_context.py` —
  `TRIGGER_ENV=ATTUNE_RUN_TRIGGER`, `_VALID_TRIGGERS={manual,
  attune-rec}` (adding `attune-heal` means touching this frozenset,
  the ops route validator in `src/attune/ops/routes/runner.py`,
  and pipeline-learner's manual-fraction weighting in
  `src/attune/pipeline_learner/mining.py`).
- Emission seams: `src/attune/workflows/telemetry_mixin.py`
  (RC-2: every BaseWorkflow path emits, report-shaped tolerated).
- Miner + readiness: `src/attune/pipeline_learner/corpus.py`
  (cutover pin, fixture-name exclusion — a DiagnosisRecord store
  should expect the same purity discipline).
- Rec/diagnosis surface: `src/attune/ops/static/js/run_view.js`
  (chips/cards/pills + run POST), `src/attune/ops/routes/`
  (runner, runs_history), curator sources in
  `src/attune/curator/sources/`.
- Round table: `src/attune/roundtable/` — `Board`, `solutions.py`
  (materialize/validate/diff/discard), `producing.py` (failure
  taxonomy, R5 cap 10), `routine.py` (`clean-run`), rotation
  ledger.
- Lessons recall: Redis `idx:attune_memory`
  (`FT.SEARCH`/`FCALL recall_digest`), hydrated from
  `.claude/lessons.md`.
- Existing shallow diagnoser: `fix-test` skill — v1 does NOT
  replace it (non-goal).

## Draft expectations

REQ items must be buildable against the seams above, honor the
four chair rulings, keep v1 scope to the nearest two or three use
cases, and name acceptance receipts (live-fire where a boundary is
crossed — a diagnosis of a real failed run from the corpus is the
canonical receipt). Non-goals from the treatment stand unless a
seat argues a boundary correction with citation.
