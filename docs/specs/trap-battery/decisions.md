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
