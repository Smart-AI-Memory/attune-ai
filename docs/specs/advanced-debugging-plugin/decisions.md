# Advanced Debugging Plugin — Decisions

## 2026-07-19 — Origin and pre-spec rulings (chair: Patrick)

Born from a live brainstorm the same day the run-record corpus
closed (RC-2 #1483, RC-3 rec-click attribution #1485): the
self-healing loop's "diagnose" stage is the gap this plugin
fills. Chair-ratified leans, folded into the treatment and the
producing run's grounding pack as hard constraints:

- **First target:** attune's own failed runs (dogfood-first).
- **Propose-only v1:** the chair rules on every fix; auto-apply is
  a later rung behind its own gate.
- **On-demand trigger first:** the run-view button; auto-diagnosis
  only as a later opt-in threshold.
- **Self-records stamped:** diagnostic runs carry `attune-heal`,
  enter the corpus, excluded from mining.

Artifacts: `treatment.md` (chair-approved one-pager),
`grounding-pack.md` (producing-run input).

## 2026-07-19 — Requirements chair-ruled per item (thread `producing-advanced-debugging-plugin-001`)

Producing run staged 8 candidates (RR-1..RR-8); the chair approved
**all eight**. RR-7 approved WITH the panel's 2-1 binding
(manual-command-only triage in v1; scheduler deferred). RR-8
approved despite `deferred_over_cap` (TR-6 cap 7) — read-only
curator source, unanimously agreed by seats.

**Run degradations (receipts, per failure-honesty):**

- `SEAT_ABSENT` round 2: claude critic seat failed
  `401 OAuth access token has been revoked` after retry — critique
  round ran on antigravity + codex only. Operational follow-up:
  re-auth the `claude` CLI before the next table run.
- `LINT_DIRTY` round 3: symbol-reality gate blocked one bare
  `producing.py` citation; staged texts carry full paths.

**Dissent register (stands until ruled):**

- Lesson-corpus ownership unresolved — graduated diagnostic
  lessons to `.claude/lessons.md` directly vs. a dedicated
  projected source. Implementation keeps lesson publication behind
  an interface until this is ruled.
- Confidence scale and the hypothesis-vs-fix-eligible threshold
  are configuration decisions; every `DiagnosisRecord` exposes the
  values used rather than hard-coding policy.

Board thread promoted with item ids 6–13; requirements compiled
deterministically by `attune.roundtable.compiler`
(`compile_requirements`, approved-only).

## 2026-07-19 — Design approved (chair)

Design ratified as drafted. Load-bearing choices: (1) a diagnosis
IS a dashboard run — the on-demand endpoint spawns
`attune diagnose <run_id>` through `RunnerService` with
`trigger=attune-heal`, reusing the RC-3 seam end-to-end;
(2) `diagnosis_records.jsonl` as the telemetry layer's third file
(inherits isolation + rotation); (3) panel/fix-loop bind to the
shipped roundtable seams, no parallel executor; (4) lesson
publication behind a `LessonPublisher` protocol and `config_used`
stamped per record (dissent honored structurally); (5) four build
phases (substrate → engine → surface → loops), one PR each with
that phase's RR receipts.

## 2026-07-19 — Tasks approved (chair)

tasks.md ratified as drafted: eight XML-decomposed tasks across
the four design phases (T1/T2 substrate, T3/T4 engine, T5
surface, T6/T7/T8 loops), one PR per phase, receipts named per
task. Execution NOT yet armed — Phase A starts on a separate
chair go. T4/T6 live-fire receipts are billable and each needs a
spend go at execution time.

## 2026-07-20 — Phase A executed (T1 + T2)

Substrate landed: `DiagnosisRecord` (+ evidence/hypothesis
dataclasses, `schema_version=1`, `config_used` stamped) in the
telemetry models; `diagnosis_records.jsonl` as the canonical third
stream (shared rotate-to-archive); `attune.diagnosis` package with
the purity-ruled loader (counted drops) and `records_for_run`;
`attune-heal` accepted by the trigger contract, route validator,
and runner env-export, excluded from mining with a counted
`dropped_attune_heal` stat.

**Deviation from tasks.md (T2):** `mining.py` untouched —
corpus-layer exclusion makes the named manual-fraction change
unreachable dead code; the trigger normalizer already maps
non-manual values to None.

**Receipts:** live-fire T1 — the real failed run `63c533fb6e46`
(2026-07-15 code-review) diagnosed, persisted, reloaded with
provenance intact; live-fire T2 — an attune-heal-stamped record in
the stream omitted by a mining pass (`dropped_attune_heal=1`); 77
affected tests serial; 2715-test breadth pass. **Honest finding:**
the real canonical run stream does not exist yet — all post-cutover
runs to date were suite-isolated; RR-1 readiness accumulation
starts from zero as of 2026-07-20.
