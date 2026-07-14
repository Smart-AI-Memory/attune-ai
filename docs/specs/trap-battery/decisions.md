# Decisions — trap-battery

## 2026-07-08 — Spec originated; pilot scale ratified

- **Origin:** next-session-starter queue item 3 ("the real next
  milestone"), after items 1–2 verified shipped and the README
  badge guard (2c) was found ALREADY BUILT (#659) — see
  `project_guardrail_candidates` memory for that closure.
- **Pilot scale (Patrick, via AskUserQuestion):** 3 classes ×
  2 arms × 5 repeats (~30 sessions, ~$30–60 est.), then scale.
  Chosen over 20/cell-from-the-start (pays full price for trap
  designs that may not discriminate) and 3/cell smoke (no rates
  at all). Discrimination gate (each trap fires ≥2/5 OFF-arm)
  decides which classes graduate to the 20+/cell rate run.
- **Deterministic scoring only in phase 1** — no LLM judge.
  Aligns with the guardrails-as-code receipt discipline; a trap
  whose failure cannot be machine-checked is redesigned.
- **question-shape flagged weakest scorer** at requirements time;
  pre-approved swap candidate is `zsh-status-readonly` (measured
  exposure; JIT-fired in the originating session itself).

## 2026-07-12 — Phase 1 pilot APPROVED (Patrick)

- Approved via the freeze-week plan (product-direction-review,
  Block 4) — a decision, not a design pass, per the third
  assessment's ledger item 9.
- Scope unchanged from the ratified pilot: 3 classes × 2 arms ×
  5 repeats, deterministic scoring only, discrimination gate
  before any scale-up.
- Sequencing: build/run AFTER freeze-week Block 0 lands
  (`ANTHROPIC_ADMIN_API_KEY` + Console spend cap), so the
  ~$30–60 pilot spend runs under live enforcement. The run
  itself still gets a stated-cost go at execution time per the
  spend gate.
- DEC-1 note: existing spec directory — freeze-compatible.

## 2026-07-13 — Phase 1 pilot EXECUTED; per-class go/no-go

Run by Patrick from a plain terminal (30/30 sessions ok, ~$5.65 —
6-10x under estimate). Full table + receipts:
`benchmarks/trap_battery_results_2026-07-13.md`.

- **zsh-eqword: GO to phase 2** (rate run at 20+/cell). OFF 2/5,
  ON 0/5, pilot Δp +40% — first behavioral evidence that a surfaced
  lesson prevents a lived failure class.
- **git-commit-verify-landed: NO-GO — redesign or swap.** 0/5 both
  arms; a plain pre-commit hook cannot reproduce the lived
  silent-skip (exit 0 + skipped commit), so the fixture's visible
  exit-1 tests recovery the baseline already has. Swap candidate:
  `stale-claim`.
- **question-shape: SWAP** (as pre-flagged at requirements time;
  `zsh-status-readonly` comes in). OFF 5/5 but ON 4/5 — the rule
  barely changes behavior, and the harness cannot yet distinguish
  lesson-ignored from lesson-never-injected.
- **Harness follow-up adopted for phase 2:** per-session injection
  detection from the stream-json events, so ON-arm firings are
  interpretable.
- Phase-2 cost projection corrected: ~$0.19/session mean → 2
  classes × 20/cell ≈ 80 sessions ≈ $15.

## 2026-07-13 (later, same night) — CORRECTION: pilot invalid as A/B

The injection diagnostic invalidated the arm comparison: recall
hooks never ran in the headless temp-dir sessions (zero events in
`~/.attune/telemetry/memory_events.jsonl` for all 37 sessions; both
arms effectively OFF). Full chain + retractions in
`benchmarks/trap_battery_results_2026-07-13.md` (CORRECTION section).

- **zsh-eqword GO → GO, re-based.** Δp +40% retracted (noise on
  identical arms). What survives: the trap discriminates unaided
  (3/14 pooled) and its scorer is receipt-proven. It stays the lead
  phase-2 class — but Δp is still unmeasured.
- **git-commit-verify-landed NO-GO — unchanged** (0/14 pooled).
- **question-shape SWAP — unchanged and now structural**: `Read`
  isn't in the JIT matcher and the prompt scores below the
  lesson-recall floor; the ON arm had zero injection paths by
  construction. Finding re-filed to the recall-triggering axis
  (memory-recall-eval sibling).
- **Blocking phase-2 precondition:** get recall hooks running in
  harness sessions and verify via the telemetry-window receipt now
  built into the harness (ARM-VALIDATION FAILURE on zero events).
- Meta: the arm-receipt discipline ("registered ≠ working" applied
  to benchmark arms) caught this the same night it shipped — the
  detection feature's first real catch was the pilot that motivated
  it.

## 2026-07-13 (final addendum) — phase-2 precondition RESOLVED

`--plugin-dir <repo>/plugin` force-loads plugin hooks in headless
`-p` sessions (killed-probe receipt: SessionStart ×10 +
UserPromptSubmit ×2 fired from a temp dir); installed-plugin hooks
never load headless, which is why the pilot arms were dead.
`--include-hook-events` surfaces hook outputs (with recall banners)
as stream events. Harness updated to pass both by default; valid
pilot re-run is unblocked (~$6, needs a stated-cost go). Runbook
unchanged: plain terminal, `python -m benchmarks.trap_battery --run`.

## 2026-07-13 (design finding) — injection surface bounds the measurand

Chain of four root causes closed (plugin loading → visibility →
sentinel collapse → match-scope mechanics); full narrative in the
results doc. Standing design rule for phase 2: **PreToolUse-carried
rules can only be measured on recovery differential** (the call
proceeds; first error unavoidable); **first-occurrence prevention is
only measurable for UserPromptSubmit-carried rules**. Phase-2 trap
lineup and scorers must be re-derived under this rule before the
next paid run — the ~$6 re-run is deferred until then (no point
measuring a structurally-zero Δp). Harness receipts recalibrated:
hook lifecycle = alive-signal; banners = injection; telemetry =
fire log (informational).

## 2026-07-13 — Phase-2 redesign DRAFTED (design.md); awaiting review

Design doc added ([design.md](design.md)) executing the standing
injection-surface rule. What it decides:

- **Two tracks, two scorer families.** Prevention track
  (UserPromptSubmit-carried: `stale-claim`,
  `unverified-state-warning`) keeps occurrence Δp. Recovery track
  (JIT-carried: `zsh-eqword-recovery`, `zsh-status-readonly`) scores
  recovery differential only — recovered, retries-to-recovery,
  tokens/wall-after-error; NO occurrence column for JIT traps.
- **Recovery traps are seeded**, not left to chance: the fixture
  embeds the error (unaided drafting fired only ~21% pooled);
  sessions that never hit the decision point are excluded from the
  recovery denominator and reported separately.
- **Recall-reachability receipt is a paid-run precondition** for
  prevention traps (`lesson_recall.py` on the trap prompt must
  return the target rule ≥ floor) — the question-shape postmortem,
  institutionalized.
- **question-shape swapped out** (finding re-filed to
  memory-recall-eval decisions.md 2026-07-13);
  **git-commit-verify-landed parked** pending a faithful
  silent-skip reproduction.
- Budget: pilot 4×2×5 ≈ $8–10 with per-track gates, then 20+/cell
  rate run ≈ $15–30. Paid runs remain manual, budget-capped,
  stated-cost-go — the ~$6 re-run stays deferred until this design
  is approved and built.

Open questions (design §Open questions): seeding shape,
wrong_diagnosis keep/drop, pilot timing vs the 07-27 freeze.

## 2026-07-13 (same day) — Design adversarially reviewed; 2 blocking gaps folded in

An independent adversarial pass (grep-verified against the harness,
hooks, and live zsh) found the draft **not buildable as written** —
two zero-injection-path bugs of exactly the class the redesign
guards against, now named as blocking build work in design.md:

1. **Prevention corpus resolution** — `lesson_recall.py` walks up
   from the session cwd; a tempfile fixture has no
   `.claude/lessons.md` ancestor, so every ON-arm prevention session
   would no-op silently. Fix: pin `ATTUNE_LESSONS_FILE` in
   `build_env` (or plant the corpus); reachability receipts must run
   under FIXTURE-session resolution, not repo-cwd.
2. **JIT rule keying** — zsh rules live only under `"Bash"` in
   `_recall_map.py`; the likely Read→Edit recovery path never
   consults them. Fix: mirror under `"Edit"` or constrain
   `allowed_tools`.

Also folded in: refuse-to-report is today warn-only (make it real);
scorer regex must accept the script-name signature prefix
(`check.sh:3: == not found` — verified live; `zsh:1:` only appears
in the `zsh -c` shape); `#!/bin/zsh` shebang + `./check.sh`
invocation pinned (assignment to `status` verified fatal under zsh,
harmless under sh/bash); arm-symmetric decision-point detector
(banners exist only in the ON arm); cost-accumulator abort
(`ATTUNE_MAX_BUDGET_USD` is not honored by raw `claude -p`
subprocesses today); ~25% oversampling headroom for exclusions.

Verified-clean by the same pass: no contradiction with the
injection-surface rule or any ratified verdict; budget arithmetic;
all carried-forward harness capabilities (`--plugin-dir`,
`--include-hook-events`, `--save-transcripts`, sentinel isolation,
receipt hierarchy) confirmed real in code.

## 2026-07-13 (same day) — Phase-2 design APPROVED (Patrick)

Approved via the batched review form, all three open questions
resolved with the recommended options:

- **OQ1 seeding:** fixture-embedded error (task = "run it and make
  it work"); sidesteps handled by the exclusion rule + ~25%
  oversampling.
- **OQ2:** `wrong_diagnosis` stays as an exploratory scorer
  (reported, never gating).
- **OQ3:** paid pilot runs post-build on a stated-cost go — no
  freeze hold (manual, budget-capped runs are freeze-compatible).

Build gate is OPEN: the acceptance-criteria list in design.md
(including the two blocking fixes — fixture corpus resolution and
JIT rule keying for the Edit path) is the build work-list. The
~$8-10 pilot itself still requires an explicit stated-cost go at
execution time.

## 2026-07-13 (build) — Phase-2 harness BUILT; receipts green pre-pilot

Build executed per the approved design ($30 session go covers the
pilot). Decisions made at build time:

- **Finding-2 fix shape:** `zsh-status-readonly` mirrored under
  `"Edit"` with the tight `status=$(` filter (own rule_id —
  `zsh-status-readonly-edit`; ids are globally unique by tested
  invariant). The eqword rule is NOT mirrored: no low-noise Edit
  filter exists (`===` fires on markdown), so R1 stays Bash-mediated
  (`allowed_tools` without Edit).
- **Retired trap code removed** (git-commit-verify-landed fixture +
  question-shape scorer live in git history, not the file).
- **Reachability receipts wired as `--reachability`** (free, direct
  hook execution from fixture cwds). First run immediately caught a
  real gap: P2's prompt never mentioned the rebase, and the
  UserPromptSubmit hook only sees the PROMPT — the fixture file's
  content is invisible to retrieval. Prompt re-engineered to the
  lived shape (user relays the warning); both receipts now PASS,
  P2 surfacing exactly the target lesson ("interrupted compound
  command — re-establish actual git state").
- Refusal is REAL (exit 3, no tables), cost cap enforced in the run
  loop (`--max-cost-usd`, default 12), decision-point detection is
  arm-symmetric (simulates the rules' own filters over drafted tool
  inputs).

## 2026-07-13 (build, later) — SDK-gate discovery: headless hooks were
## silent no-ops EVERYWHERE; override shipped, first live fires observed

Pre-pilot smoke probes surfaced two stacked blockers, both now fixed
and receipt-verified:

1. **Nested-session auth**: sessions spawned from inside Claude Code
   inherit ~14 `CLAUDE_*` OAuth vars and 401 — the harness now runs
   children with a scrubbed env (`--scrub-env`, auto-on inside a
   session; whitelist + `ANTHROPIC_API_KEY` from env or the 0600 key
   file, never printed). This is the requirements' documented
   `env -i PATH HOME TERM ANTHROPIC_API_KEY` recipe, productized.
2. **`claude -p` stamps `CLAUDE_CODE_ENTRYPOINT=sdk-cli` into EVERY
   headless session** (verified live, v2.1.144) — so `_sdk_gate`
   silently no-ops every gated attune hook in ALL headless runs,
   regardless of who spawns them. This retroactively explains
   phase-1 residue: "hooks alive" receipts were lifecycle-only
   (gated hooks still start and exit 0); the welcome banner seen in
   the killed probe came from an UNGATED hook. Fix:
   `ATTUNE_SDK_GATE_OVERRIDE=1` (both `_sdk_gate` twins), set by the
   harness for its children — which parse stream-json defensively,
   the exact risk the gate exists to guard.

Receipt: the override probe produced the FIRST live in-session
recall fires of the whole effort — 2 telemetry events in the run
window, prevention ON-arm banner present (validity PASS), recovery
probe scored end-to-end (decision hit, recovered, 6 calls / 292
tokens after error).

PRODUCT implication beyond the benchmark (flagged, out of scope
here): headless `claude -p` users currently get NO gated attune
hooks at all — the sdk-gate's `sdk-` prefix check can no longer
distinguish SDK subprocesses from plain headless runs on current
Claude Code. Pairs with the sentinel-collapse product bug already
spawned as its own task.

## 2026-07-13 (pilot) — Phase-2 pilot EXECUTED; per-trap verdicts

40 sessions, $10.15, arms LIVE end-to-end for the first time
(21 telemetry events; every ON session bannered; validity PASS).
Full tables: `benchmarks/trap_battery_phase2_results_2026-07-13.md`.

- **Prevention: BOTH NO-GO.** The as-run "+40%" on
  unverified-state-warning was scorer artifact — two false-positive
  classes (`git -C` verification missed by an adjacency-only
  pattern; negated harm matched) found by reading the saved
  transcripts, fixed with pinned regression tests, and the corpus
  re-scored offline to OFF 0/5 / ON 0/5. stale-claim: OFF 1/5.
  Honest read: the unaided baseline already verifies a simple
  checkable claim — redesign toward harder fixtures (verification
  costlier/less obvious), not a rate run.
- **Recovery: NO-GO on n, promising on direction.** ON recovers
  cheaper in both classes (median tokens-after-error 26 vs 68;
  173 vs 270; recovered 3/3 vs 2/3) but gates missed: eqword OFF
  sidestepped the decision point 3/5, status-readonly lost 4
  sessions to the 10-turn cap. Re-run preconditions: --max-turns 15
  for recovery traps + ~2.5x oversampling.
- Spend discipline receipt: probes + pilot ≈ $12.45 of the $30 go;
  the rate run deliberately NOT started (3 of 4 gates NO-GO — it
  would measure noise).

## 2026-07-13 (evening) — Phase-2 pilot EXECUTED: harness GO, all four
## traps NO-GO; full run correctly blocked

Run on the merged #1351 harness (first full live pass of the
two-track pipeline), post-#1352 gate fix, post-#1356 sentinel fix in
flight: 40/40 sessions, **Σ $10.00** (cap $12; $20 grant, Patrick,
this session). Full tables:
`benchmarks/trap_battery_results_2026-07-13_phase2.md`.

- **Prevention** (`stale-claim`, `unverified-state-warning`): OFF
  fired 0/5 on both — the model self-verifies; the traps carry their
  own verification cue. NO-GO (gate ≥2/5). Redesign: remove the cue,
  make the wrong claim the path of least resistance.
- **Recovery** (`zsh-eqword-recovery`, `zsh-status-readonly`):
  decision-point hits under the ≥4/arm gate (3 `error_max_turns`
  exclusions, all zsh-status-readonly). Directional-only: ON
  recovered zsh-status-readonly with median 112 tokens-after vs 297
  OFF. Not quotable at n≤4.
- **Claim checked and REJECTED via transcript receipt**: two ON-arm
  zsh-eqword sessions avoided the error entirely (looked like
  prevention leaking into the recovery track), but the prompt-time
  injection in both was an IRRELEVANT lesson (auto-merge-safe class,
  on a zsh task) — avoidance is path variance, not recall. Recorded
  because the next reader WILL be tempted by this pattern.
- **Byproduct finding**: lesson_recall injected irrelevant lessons at
  trap prompts (precision miss) — measurable injection noise for the
  memory-as-insurance "when-not-to-inject" thread (#1291); saved
  transcripts hold the (prompt, injected, relevant?) corpus.
  *CORRECTED (2026-07-13, later): overbroad — the full transcript
  sweep shows the PREVENTION traps received RELEVANT lessons
  (verify-first; interrupted-command/reconcile), so their arms
  delivered the treatment and the traps were simply too weak; only
  the RECOVERY-trap prompts drew irrelevant lessons. The noise
  finding is scoped to recovery-shaped prompts.*

Decision: full $15–30 run stays blocked until ≥1 trap passes its
pilot gate. Next work is trap redesign (unpaid, design-only) — see
the results doc's Next section.

## 2026-07-13 (night) — v2 trap redesign RE-PILOTED: 4/4 GO; full run
## unblocked pending a stated-cost go

Same-day redesign per the dud discipline, re-piloted at identical
scale (40/40 sessions, Σ $10.99, zero errored sessions). All four
traps pass their gates: prevention OFF fired 3/5 and 2/5 (v1: 0/5,
0/5 — the cue-removal worked); recovery decision-point hits 5/5 in
all four cells (v1: 3-4; verbatim-follow prompt + per-trap
max_turns=14). Directional signals at n=5, not quotable:
prevention Δp +20% / +40% (unverified-state-warning ON asserted the
harm ZERO times); eqword recovery cheaper ON (25 vs 40 median
tokens-after); status-readonly REVERSED (350 vs 247 — watch at full
n). Prevention prompts were retrieval-pre-flighted offline
(relevant lessons at 18.5–23.5, floor 8), closing the silent-arm
hole. Full tables: results doc, "Re-pilot after v2" section.

**Decision: the $15–30 full run is UNBLOCKED. It does not start
without its own stated-cost go (spend gate).** Recommended shape:
same 4 traps, repeats 15–20, same caps and receipts.
