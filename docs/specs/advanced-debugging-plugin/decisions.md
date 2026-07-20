# Advanced Debugging Plugin — Decisions

**Status:** shipped (2026-07-20) — spec complete (#1503)

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

## 2026-07-20 — Phase B executed (T3 + T4) with live-fire receipt

Engine landed: priors recall (explicit degradation), deterministic
bounded evidence packs, the seat panel on the shipped roundtable
machinery, `engine.diagnose()`, and `attune diagnose <run_id>`.
44 diagnosis tests serial; 724-test breadth.

**T4 live-fire receipt (chair-armed spend, 2026-07-20).** A real
keyless workflow failure was generated into the REAL canonical
stream (run `85c88fd9…`, code-review, "path argument is required" —
the stream's first real record), then `attune diagnose` ran with
REAL seats: claude ABSENT (revoked OAuth — the absent-seat receipt
observed live, 2 retry invocations), antigravity + codex answered
independently; BOTH top hypotheses correctly identified the missing
path argument (high confidence), both offered a distinct
low-confidence regression alternative citing the git-log evidence;
4 invocations under the cap of 10; no dissent (material agreement
detected). DiagnosisRecord `3264a8f6107b` persisted to the real
diagnosis stream with `config_used` stamped and reload verified.

**Observation for Phase C/D tuning:** priors degraded
`no-terms-extracted` — the symptom text ("path argument is
required") carries no error-class/module tokens; term extraction
should also derive terms from the workflow name and argument names.
Recorded, not fixed here.

## 2026-07-20 — Phase C executed (T5)

On-demand surface landed: `POST /runs/{run_id}/diagnose` (token +
allow-run gated, failed-terminal-only, attune-heal sources
refused, idempotent via `records_for_run`), dispatching ONE runner
subprocess `attune diagnose <run_id>` stamped `attune-heal`; the
run-view "Why did this fail?" button (terminal-failed runs only,
explicit click, never auto-starts) and the "diagnosed" chip;
`Run.extra_args` threading + a `diagnose` case in the runner's
command builder.

**Design deviation (recorded):** dashboard run ids (12-hex) and
telemetry run ids (uuid4) are DIFFERENT id spaces —
`find_source_run` gained an ops-record fallback that synthesizes a
source `WorkflowRunRecord` from the persisted ops run, so the
button's ops id diagnoses correctly.

**Receipts:** endpoint suite incl. a real subprocess dispatch
round-trip observing `ATTUNE_RUN_TRIGGER=attune-heal` + the source
run id in the child argv; 1516-test ops+diagnosis breadth;
source-level no-auto-start guards; BROWSER receipt — the ops
dashboard restarted on worktree code (launch.json MAPPING fix,
local-only) renders the button beside the failed chip on the real
2026-07-15 run `63c533fb6e46`. The button was deliberately NOT
clicked — a click launches a billable panel run (spend-gated).

## 2026-07-20 — Phase D executed (T6 + T7 + T8)

Loops landed: the propose-only fix loop binding the solutions
lifecycle (threshold gate by scale index, one repair round,
reviewer != proposer, failed validation visible, discard in
finally with a leaked-worktree sweep assertion); the manual-only
triage command (`python -m attune.diagnosis.triage`, dry-run mode,
batch cap, heal/success/diagnosed exclusions, hypothesis
clustering that never merges conflicting evidence, board digest
with R8 stated); the read-only curator source with ALLOWLIST
redaction; and the `LessonPublisher` protocol whose only v1
implementation renders for the chair (source-level guard: no write
primitives in the module).

**Deviations (recorded):** (1) triage is NOT registered in
`roundtable.routine.ROUTINES` — the routine runner's check-battery
shape doesn't fit a diagnosis batch, and standalone keeps the 2-1
manual-only binding structurally true (guard test asserts
absence); (2) T6's seat-side live-fire (a real seat proposing a
real fix) is deferred to a chair spend go — the MECHANICAL
boundary is live-fired in tests (real `git worktree` materialize,
real py-compile validation receipts, real discard against a real
repo), only the seats are mocked.

**Receipts:** 69 diagnosis tests serial (25 new: threshold
gating with zero spend below threshold, repair round, visible
failed-validation, reviewer-differs, worktree-sweep, selection
exclusions, cap, cluster/digest honesty, redaction allowlist,
graduation lint gates, no-write guard); 2329-test breadth over
diagnosis/curator/roundtable/ops/telemetry.

**Still open:** the two dissent-register rulings (lesson-corpus
ownership; confidence-scale value review) — the interface keeps
both unblocking; and the deferred seat-side live-fires (T6 fix
proposal, full browser click-through) under one future spend go.

## 2026-07-20 — Deferred live-fires executed (chair-armed); spec complete

**Live-fire 1 — browser click-through (full circle).** On the
dashboard served from merged main: a fresh REAL failed run was
created through the production runner (`diagnose` dispatched with
no argument — exit 2, zero spend), its run view rendered the
"Why did this fail?" button beside the failed chip, and a REAL
CLICK dispatched `attune diagnose` stamped `attune-heal`; the
diagnostic run streamed live on its own run view (chained-from
badge rendered) and completed exit 0. Panel: **3 seats, 0 absent,
3 invocations** — claude, antigravity, and codex each
independently identified the exact root cause (missing `run_id`
positional). `DiagnosisRecord 40482304b805` persisted to the
canonical stream; the source run's view now renders
`diagnosed: 40482304b805` with the button retired (idempotency
surface verified live). An earlier diagnosis (`7e751fed728a`,
03:04, from a pre-logout session stretch) independently confirmed
the chip path on run `63c533fb6e46`.

**Live-fire 2 — fix loop with real seats (honest-failure
receipt).** `run_fix_loop` on the high-confidence real diagnosis
`7e751fed728a` against the main repo. Findings, per TAC-4
(failures presented failed-with-receipts, never laundered):

- claude seat: stored OAuth revoked in shell contexts →
  `proposer-absent` (recipe-scrub verified working as designed —
  the dashboard subprocess carries its own credential).
- antigravity as proposer: exit 0 with EMPTY output — `--mode
  plan` (reasoning-only, correct for R1 positions) structurally
  cannot emit file-block code proposals. Seat-ROLE fit is real:
  plan-mode seats review; code-native seats propose.
- codex as proposer, antigravity reviewing: codex answered BOTH
  rounds, **the one-repair-round path fired live**, and both
  proposals failed materialize honestly (`unified diff names no
  target files`) — the loop refused to launder, main tree
  byte-identical before/after, zero leaked scratch worktrees.

**Named follow-ups (recorded, not fixed here):**

1. The diagnosis engine's own execution emits NO canonical run
   record (`attune diagnose` is a CLI command, not a workflow —
   RC-2's seam has nothing to stamp), so `attune-heal` records
   exist today only in the ops store; the mining exclusion guards
   an empty set until the engine emits its own heal-stamped
   record.
2. Proposer-brief hardening for codex's output format (accept its
   diff/prose interleaving or teach the format by worked example,
   the producing-run precedent) + roster role-fit (proposer must
   be a code-emitting seat).
3. claude CLI re-auth owed (`claude login`) for shell-context
   seats.

With all four phases, all eight RR receipts, and both live-fires
executed, this spec is COMPLETE; the follow-ups above are the v1.1
backlog.

## 2026-07-20 — First-content triage of the diagnoses stream (q-briefing-triage-002 A3, chair ruled)

The stream's first three records are all artifacts of this spec's own
ship day, not operational failures:

- `3264a8f6107b` (run `85c88fd9…`, "path argument is required") and
  `7e751fed728a` (run `63c533fb46…`, ops exit 1) are the live-fire
  receipt runs named in this file's Phase A/B entries.
- `40482304b805` (run `0910cf106403`, diagnose exit 2, 05:49 UTC)
  falls inside the overnight Phase C/D dogfood window; treated as
  dogfood pending contrary evidence.

The canonical stream was NOT hand-edited: `store.py` is
read-only-by-design and append-only via `TelemetryStore.log_diagnosis`
with no dedupe, so a "closure" append would double records instead of
updating them. Two queued follow-ons (behind the T2 hygiene PR, per
the codex no-parallel-program risk):

1. **Phase B priors defect** — all 3/3 real records carry
   `priors_degraded: no-terms-extracted`: the term extractor gets
   zero signal from real symptoms. One fix task; not inline.
   (CORRECTED 2026-07-20, D17: this entry originally also claimed
   the 05:49 record's hypotheses had "EMPTY summaries" — that was
   the recording probe reading a nonexistent `summary` key; the
   field is `statement` and the hypotheses are substantive. The
   defect was only ever the extractor.)
2. **Origin-tag + closure seam** — an `origin` field
   (live-fire | dogfood | operational) stamped at creation, a
   status-update seam (last-wins by `diagnosis_id` or a tombstone
   record), and automated-suite exclusion for the diagnoses curator
   source, mirroring the RR corpus suite-isolation rule. Ruled
   2-1: tag, never retro-delete (D3 no-backfill spirit).

## D17 — Priors term extraction fixed for terse operational symptoms (2026-07-20, chair "go 2")

The four Phase B shape patterns (exception classes, dotted paths,
backticks, `*.py`) all missed the real symptom class — terse
operational phrases like "path argument is required" and "ops run
failed (exit 1, sdk_error_kind=None)" — degrading priors on 3/3
live records. Two-part fix in `diagnosis/priors.py`:

- a fifth shape pattern for snake_case identifiers
  (`sdk_error_kind`), always active;
- a stopword-filtered plain-word FALLBACK that fires only when
  every shape pattern missed — generic failure vocabulary
  (failed/error/exit/run/...) is stopworded so recall keys on the
  specific nouns ("path", "code-review"), and traceback-shaped
  text extracts exactly what it did before (precision unchanged,
  test-pinned).

Receipts: the three live symptoms as regression tests (each now
extracts recall-able terms; "path argument is required" →
`["path", "code-review"]`), fallback-suppression test on
traceback-shaped text; diagnosis suite 73 passed. Also corrected
the A3 entry's false "empty hypothesis summaries" claim (probe
misread, see annotation there).

## D18 — Origin-tag + closure seam shipped; A3 disposition executed (2026-07-20, chair "go 3")

- `DiagnosisRecord.origin` (operational | dogfood | live-fire),
  stamped at creation (`diagnose(origin=...)`; `attune diagnose
  --origin`). Legacy records load as operational (tolerant
  from_dict).
- Closure seam: the loader is now last-wins by `diagnosis_id` with a
  `dropped_superseded` counter — an update is a re-appended full
  record (`attune.diagnosis.retag_origin`), the stream stays
  append-only, nothing is rewritten or deleted. The status enum
  stays CLOSED: tagging an artifact's origin IS its closure, because
  the diagnoses curator source surfaces operational records only.
- A3 executed with the new seam: 3264a8f6/7e751fed retagged
  live-fire, 40482304 retagged dogfood. Receipt: loader shows 3
  superseded lines counted; the briefing source now surfaces 0
  diagnosis items.
- Automated-suite exclusion: already carried by the ATTUNE_HOME
  test-isolation fixture + FIXTURE_NAMES drop; origin covers the
  remaining dogfood/live-fire-in-real-home class.

Receipts: 8 contract tests in
`tests/unit/diagnosis/test_origin_seam.py` (default + legacy load,
last-wins + superseded counter, retag round-trip, vocabulary guard,
source exclusion); diagnosis+curator 218 passed.

## 2026-07-20 — v1.1 backlog item 2: proposer-brief hardening + roster role-fit (chair-picked)

Both remedies from live-fire 2's named follow-up, executed:

- **Roster role-fit.** `PLAN_ONLY_SEATS` (routine.py, deny-list —
  antigravity's `--mode plan` structurally cannot emit file blocks;
  new seats default code-emitting). `run_fix_loop` now: (1) selects
  the proposer only from code-emitting seats, with an explicit
  `no-code-emitting-proposer` disposition (zero spend) when the
  roster has none; (2) on `proposer-absent`, falls to the NEXT
  code-emitting seat (the live-fire's manual recovery — claude
  absent → codex proposed, antigravity reviewed — is now the loop's
  own behavior; `absent_proposers` recorded); `failed-materialize`
  stays terminal — the loop never seat-shops a format failure;
  (3) picks the reviewer skipping the proposer AND known-absent
  seats; a roster with no distinct reviewer is `rejected`, never
  laundered to `proposed`.
- **Proposer-brief hardening** (teach-by-worked-example, the
  producing-run precedent — `TAG_EXAMPLE` class): literal
  `FILE_BLOCK_EXAMPLE` embedded in the brief. Root-cause note: the
  old repair message ("unified diff names no target files / Fix the
  format") actively steered seats TOWARD unified diffs; the repair
  brief now names the materialize failure and restates the
  file-block contract with the example. Accept-diff/prose-
  interleaving was NOT built — codex's exact output shape wasn't
  captured, so parser guessing is speculative; revisit only if a
  worked-example round still fails live.

Receipts: 14 fix-loop tests serial (5 new role-fit: plan-only skip,
all-plan-only zero-spend, absent-fallback with reviewer exclusion,
no-seat-shopping, solo-roster honesty; 1 new brief guard);
diagnosis+roundtable 243 passed serial.
