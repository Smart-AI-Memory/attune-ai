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
