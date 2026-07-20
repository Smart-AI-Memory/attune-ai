# Advanced Debugging Plugin — Tasks

**Status:** shipped (2026-07-20) — all four phases shipped, live-fires receipted; see decisions.md. Eight tasks across
the design's four phases (A substrate, B engine, C surface,
D loops). One PR per phase; each task names its RR receipts.
Execute in order — every task builds on the previous task's
landed seams.

## Phase A — substrate

### T1 — DiagnosisRecord schema + store (RR-1)

```xml
<task id="adp-1" name="diagnosis-record-and-store">
  <objective>
    Ship the versioned DiagnosisRecord and its jsonl store —
    the substrate every later task writes through.
  </objective>
  <context>
    <existing-code path="src/attune/models/telemetry/data_models.py">
      WorkflowRunRecord: dataclass + from_dict tolerance idiom
      (additive optional fields) to mirror.
    </existing-code>
    <existing-code path="src/attune/models/telemetry/storage.py">
      TelemetryStore: canonical ATTUNE_HOME resolution +
      50 MB rotate-to-archive; add diagnoses_file beside
      workflows_file so isolation and rotation are inherited.
    </existing-code>
    <existing-code path="src/attune/pipeline_learner/corpus.py">
      Purity discipline to mirror: fixture-name exclusion,
      cutover pin, malformed-line skip counters.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/diagnosis/__init__.py">Public exports.</file>
    <file path="src/attune/diagnosis/store.py">
      load_diagnoses(): canonical loader with purity rules;
      records_for_run(source_run_id) for idempotency lookups.
    </file>
    <file path="tests/unit/diagnosis/test_record_store.py">
      Round-trip, from_dict on pre-v1 dicts, purity exclusions,
      ATTUNE_HOME isolation drift guard, rotation inheritance.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/models/telemetry/data_models.py">
      Add DiagnosisRecord (+ nested evidence/hypothesis/fix
      dataclasses) per design.md §1, schema_version=1,
      config_used stamped.
    </file>
    <file path="src/attune/models/telemetry/storage.py">
      diagnoses_file property + log_diagnosis(record); same
      rotation policy as workflow runs.
    </file>
  </files-to-modify>
  <validation>
    <check>Serial pytest tests/unit/diagnosis + tests/unit/telemetry — pass</check>
    <check>Live-fire: persist + reload a DiagnosisRecord for a REAL failed run from ~/.attune/telemetry/workflow_runs.jsonl without provenance loss (RR-1 receipt)</check>
  </validation>
  <risks>
    <risk severity="low">Schema over-design — keep nested dataclasses minimal; v2 can extend (schema_version exists for this).</risk>
  </risks>
</task>
```

### T2 — attune-heal trigger extension (RR-2)

```xml
<task id="adp-2" name="attune-heal-trigger">
  <objective>
    attune-heal becomes a valid trigger end-to-end while staying
    excluded from mining, triage selection, and graduation.
  </objective>
  <context>
    <existing-code path="src/attune/models/telemetry/run_context.py">
      _VALID_TRIGGERS frozenset + resolve_run_trigger (junk →
      manual). The RC-3 seam threads env → record.
    </existing-code>
    <existing-code path="src/attune/ops/routes/runner.py">
      _read_run_body trigger validation (manual | attune-rec).
    </existing-code>
    <existing-code path="src/attune/pipeline_learner/mining.py">
      manual-fraction weighting; corpus.py eligibility filter.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/models/telemetry/run_context.py">
      Add "attune-heal" to _VALID_TRIGGERS.
    </file>
    <file path="src/attune/ops/routes/runner.py">
      Route accepts attune-heal (engine-dispatched runs).
    </file>
    <file path="src/attune/pipeline_learner/mining.py">
      attune-heal counts as non-manual in manual-fraction.
    </file>
    <file path="src/attune/pipeline_learner/corpus.py">
      attune-heal records excluded from eligible set.
    </file>
    <file path="tests/unit/telemetry/test_run_record_corpus.py">
      Trigger-contract cases extended.
    </file>
    <file path="tests/unit/pipeline_learner/test_learner.py">
      Exclusion + weighting cases.
    </file>
  </files-to-modify>
  <validation>
    <check>Integration receipt: emit an attune-heal-stamped record, run a mining pass, show omission (RR-2 receipt)</check>
    <check>Serial pytest of both touched test files — pass</check>
  </validation>
  <risks>
    <risk severity="low">Widening _VALID_TRIGGERS silently reclassifies junk env values — junk still resolves manual; only the exact literal passes.</risk>
  </risks>
</task>
```

## Phase B — engine core

### T3 — load, priors, evidence pack (RR-4)

```xml
<task id="adp-3" name="priors-and-evidence">
  <objective>
    The diagnosis pipeline's deterministic front half: source-run
    load, lesson-prior recall, bounded evidence pack.
  </objective>
  <context>
    <existing-code path="src/attune/models/telemetry/storage.py">
      Run-corpus read path for source-run load.
    </existing-code>
    <existing-code path=".claude/CLAUDE.md">
      Shared-memory recall recipe: FCALL recall_digest /
      FT.SEARCH idx:attune_memory, OR-joined terms; degrade
      silently when Redis is unreachable — here degrade LOUDLY
      into the record (priors_degraded reason), per RR-4.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/diagnosis/engine.py">
      diagnose(run_id, config) orchestrator skeleton: load →
      priors → evidence (panel wired in T4); refuses non-failed
      and attune-heal sources.
    </file>
    <file path="src/attune/diagnosis/priors.py">
      Error-shape term extraction + recall; returns lesson refs
      or an explicit degraded reason. Priors are a distinct
      evidence kind — never merged with observed evidence.
    </file>
    <file path="src/attune/diagnosis/evidence.py">
      Bounded-bytes deterministic pack: record fields, log tail,
      cited-file excerpts, recent git log. Largest-value-first
      truncation order per design.md.
    </file>
    <file path="tests/unit/diagnosis/test_priors_evidence.py">
      Degraded-mode explicitness, kind separation, byte-budget
      truncation determinism, source-run refusal rules.
    </file>
  </files-to-create>
  <validation>
    <check>Receipt: a known lesson surfaces as a prior for a matching error shape; an unsupported recalled claim is NOT promoted to evidence (RR-4 receipt)</check>
    <check>Redis stopped → diagnosis proceeds with priors_degraded set</check>
  </validation>
  <risks>
    <risk severity="medium">Term extraction quality drives prior relevance — start with error-class + module tokens; tune later, never block.</risk>
  </risks>
</task>
```

### T4 — panel, synthesis, CLI (RR-5)

```xml
<task id="adp-4" name="panel-and-cli">
  <objective>
    The receipted diagnosis panel and the `attune diagnose`
    command — a DiagnosisRecord written end-to-end.
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/producing.py">
      Seat invocation recipes, FAILURE_CODES, R5 cap pattern,
      absent-seat degradation.
    </existing-code>
    <existing-code path="src/attune/cli_minimal.py">
      Command registration pattern (see gates_commands.py).
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/diagnosis/panel.py">
      ≥2 independent seats over the same pack; moderator
      synthesis (ranked hypotheses, confidence, dissent);
      failures classified onto FAILURE_CODES; cap 10.
    </file>
    <file path="src/attune/cli_commands/diagnosis_commands.py">
      attune diagnose &lt;run_id&gt; [--config overrides].
    </file>
    <file path="tests/unit/diagnosis/test_panel.py">
      Synthesis retention of dissent, absent-seat degradation,
      classified failure path, cap enforcement (mock seats —
      panel logic, not LLM output, is under test).
    </file>
  </files-to-create>
  <validation>
    <check>Live-fire (chair-armed spend): `attune diagnose` a real failed corpus run end-to-end; DiagnosisRecord lands with panel receipts (Phase-B canonical receipt)</check>
    <check>Serial unit pass; one seat absent → record shows absence, diagnosis completes</check>
  </validation>
  <risks>
    <risk severity="medium">Seat auth fragility (observed 401) — absent-seat path is first-class and tested, not exceptional.</risk>
  </risks>
</task>
```

## Phase C — surface

### T5 — endpoint, button, chip (RR-3)

```xml
<task id="adp-5" name="on-demand-surface">
  <objective>
    "Why did this fail?" from the run view: validated endpoint,
    idempotent dispatch, diagnosis linked back to its source.
  </objective>
  <context>
    <existing-code path="src/attune/ops/routes/runner.py">
      start_run: token + allow_run gates, RunnerBusyError shape;
      the RC-3 trigger threading the endpoint reuses.
    </existing-code>
    <existing-code path="src/attune/ops/static/js/run_view.js">
      Chip/button conventions, attuneClientHeaders, 409 handling.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/ops/routes/runner.py">
      POST /runs/{run_id}/diagnose: validate failed+terminal
      source, idempotency via store.records_for_run, dispatch
      `attune diagnose &lt;id&gt;` with trigger=attune-heal.
    </file>
    <file path="src/attune/ops/static/js/run_view.js">
      Button on terminal-failed runs only; navigate to the
      diagnostic run's view; completed-diagnosis chip links back.
    </file>
    <file path="tests/unit/ops/test_diagnose_endpoint.py">
      (create) 404 unknown, 400 non-failed, idempotent second
      call returns existing link, dispatch carries attune-heal
      (subprocess env round-trip mirroring
      test_run_trigger_attribution.py).
    </file>
  </files-to-modify>
  <validation>
    <check>Integration receipt: endpoint → runner → child env ATTUNE_RUN_TRIGGER=attune-heal observed (RR-3 receipt)</check>
    <check>No auto-start: page load and run ingestion dispatch nothing (source-level guard test)</check>
  </validation>
  <risks>
    <risk severity="low">Busy-lock contention: diagnosis occupies the single-run slot — 409 surface already handles it.</risk>
  </risks>
</task>
```

## Phase D — loops

### T6 — propose-only fix loop (RR-6)

```xml
<task id="adp-6" name="fix-proposal-loop">
  <objective>
    Confidence-gated fix proposals through the solutions seams —
    materialize, validate, cross-seat review, discard. Never
    touches the user's tree.
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/solutions.py">
      materialize / validate / diff_against_base / discard —
      bind, don't reimplement (TAC-4 honesty).
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/diagnosis/fix_loop.py">
      Threshold gate (config_used.fix_proposal_threshold), one
      repair round max, reviewer seat != proposer seat, full
      lifecycle into proposed_fix, unconditional discard.
    </file>
    <file path="tests/unit/diagnosis/test_fix_loop.py">
      Threshold gating, reviewer-differs invariant, failed
      validation stays visible, discard always runs.
    </file>
  </files-to-create>
  <validation>
    <check>Live-fire receipt: scratch-worktree materialize + one real check + different-seat review + discard; `git status` in the user worktree unchanged before/after (RR-6 receipt)</check>
  </validation>
  <risks>
    <risk severity="medium">Scratch-worktree leak on crash — discard in finally; leaked-worktree sweep assertion in tests.</risk>
  </risks>
</task>
```

### T7 — failed-run triage routine (RR-7)

```xml
<task id="adp-7" name="triage-routine">
  <objective>
    Manual-command batch triage: bounded failed-run selection,
    per-failure diagnosis, clustered digest. R8 absolute.
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/routine.py">
      clean-run pattern: battery → deliberation → digest thread;
      registration + dry-run mode.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/diagnosis/triage.py">
      Select last N non-attune-heal failures since prior digest
      (triage_batch_max cap); cluster repeated hypotheses without
      merging conflicting evidence; digest thread
      routine-failed-run-triage-&lt;date&gt;.
    </file>
    <file path="tests/unit/diagnosis/test_triage.py">
      Selection exclusions (attune-heal, non-failed), batch cap,
      no promotion at any stage, digest links every conclusion to
      its DiagnosisRecord.
    </file>
  </files-to-create>
  <validation>
    <check>Routine receipt: eligible failures in, self-records out, zero writes to tracked files (RR-7 receipt)</check>
    <check>Manual command only — no scheduler registration exists (grep-level guard)</check>
  </validation>
  <risks>
    <risk severity="low">Digest volume — clustering caps rendered hypotheses per cluster.</risk>
  </risks>
</task>
```

### T8 — curator source + graduation interface (RR-8, dissent)

```xml
<task id="adp-8" name="curator-and-graduation">
  <objective>
    Read-only curator grounding over diagnoses, and the
    LessonPublisher interface that keeps corpus ownership
    unruled but unblocking.
  </objective>
  <context>
    <existing-code path="src/attune/curator/sources/spec_drift.py">
      Newest curator-source shape to mirror.
    </existing-code>
    <existing-code path="src/attune/roundtable/__init__.py">
      LessonCandidate lint (receipt-or-waiver) — graduation
      renders through it; publication stays behind the protocol.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/curator/sources/diagnoses.py">
      Canonical loader + mining-identical exclusions; provenance,
      status, confidence, dissent; diffs/evidence redacted unless
      detailed view requested.
    </file>
    <file path="src/attune/diagnosis/graduation.py">
      LessonPublisher protocol + render-for-chair impl (the ONLY
      v1 impl); graduation requires verification receipt + chair
      approval; attune-heal diagnoses never graduate.
    </file>
    <file path="tests/unit/diagnosis/test_curator_graduation.py">
      Exclusion parity with mining, redaction default, protocol
      has no direct-corpus-write impl in v1 (source-level guard).
    </file>
  </files-to-create>
  <validation>
    <check>Source-level receipt: deterministic grounding doc from persisted diagnoses; ineligible records excluded (RR-8 receipt)</check>
  </validation>
  <risks>
    <risk severity="low">Redaction misses a sensitive field added later — redact by allowlist, not blocklist.</risk>
  </risks>
</task>
```

## Execution notes

- Receipts re-run centrally before each phase PR ships (delegation
  receipts rule) — a task's self-report is never the receipt.
- Live-fire panel/fix-loop tasks (T4, T6) are billable — each
  needs a chair spend go at execution time (spend gate).
- The dissent register's two open items (lesson-corpus ownership,
  confidence-scale values) must be ruled before T8 ships its
  defaults; T8's interface design keeps T1–T7 unblocked either
  way.
