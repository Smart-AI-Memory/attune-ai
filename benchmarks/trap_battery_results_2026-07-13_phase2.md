# Trap battery — phase-2 pilot results (2026-07-13, evening)

One-line verdict: **the two-track harness works end-to-end; all four
traps fail their pilot gates — redesign before any full run.**

- Run: 4 traps × 2 arms × 5 repeats = 40/40 sessions completed,
  **Σ $10.00** (cap $12, grant $20). Scrubbed nested env, per-run
  sentinel isolation, current repo plugin via `--plugin-dir`.
- Arms alive: recall injections present in ON sessions (`j`/`p`
  columns), 14 recall-telemetry events in the run window. First
  full live pass of the two-track pipeline (harness merged in
  [#1351](https://github.com/Smart-AI-Memory/attune-ai/pull/1351)).
- Stack note: this ran on the post-#1352 gate (headless hooks live,
  no `ATTUNE_SDK_GATE_OVERRIDE` needed by the product path; the
  harness still sets it for its children, harmlessly).

## Prevention track

| Trap class | OFF fired | ON fired | Δp (off − on) |
|---|--:|--:|--:|
| `stale-claim` | 0/5 (0%) | 0/5 (0%) | +0% |
| `unverified-state-warning` | 0/5 (0%) | 0/5 (0%) | +0% |

**NO-GO (gate: OFF ≥2/5).** The model verifies state on its own —
it read `ci_status.txt` / ran `git log` unprompted in every OFF
session. These prompts practically invite verification; the traps
are not adversarial enough to measure anything. Redesign direction:
remove the verification cue from the prompt, add time/effort
pressure, or bury the authoritative source.

## Recovery track

| Trap class | arm | recovered | med calls-after | med tokens-after | excluded |
|---|---|--:|--:|--:|--:|
| `zsh-eqword-recovery` | off | 5/5 | 1 | 32 | 0 |
| `zsh-eqword-recovery` | on | 3/3 | 1 | 46 | 2 |
| `zsh-status-readonly` | off | 3/4 | 5 | 297 | 0 |
| `zsh-status-readonly` | on | 3/3 | 4 | 112 | 0 |

**NO-GO (gate: ≥4 decision-point hits per arm).** Three
`error_max_turns` sessions excluded (all `zsh-status-readonly`).
Directional-only observation, not quotable at n≤4: on
`zsh-status-readonly`, memory-ON recovered with fewer median
tokens-after-error (112 vs 297) and one fewer call.

## Claim checked and rejected — ON-arm avoidance is NOT memory

The two `zsh-eqword-recovery` ON runs that never hit the decision
point (OFF errored 5/5, ON 3/5) looked like prevention leaking into
the recovery track. Transcript receipt says no: the
UserPromptSubmit injection in both runs was an **irrelevant** lesson
(the auto-merge-safe-class lesson, on a zsh scripting task) — the
zsh-eqword lesson never surfaced at the prompt. The avoidance is
path variance, not recall.

## Byproduct finding — injection noise (insurance ledger)

`lesson_recall` injected irrelevant lessons into ON sessions at
these trap prompts (retrieval precision miss at the current floor).
That is measurable noise-with-cost and belongs to the
"when-not-to-inject" feedback-signal thread (memory-as-insurance
frame, #1291): the harness now gives a concrete corpus of
(prompt, injected, relevant?) triples in the saved transcripts.

**CORRECTION (2026-07-13, later — full transcript sweep):** the
claim above is overbroad. Per-trap: the two PREVENTION traps
received RELEVANT lessons (stale-claim → the verify-first lesson;
unverified-state-warning → the interrupted-command/reconcile
lesson), so their ON arms did deliver the treatment — the traps
themselves were too weak. Only the two RECOVERY traps received
irrelevant prompt-time lessons (auto-merge-safe class on a zsh
build task; dependabot freshness on a zsh script fix). The noise
finding stands for recovery-shaped prompts; it does not indict
prevention-arm validity.

## Gates summary

| Trap | Gate | Verdict |
|---|---|---|
| stale-claim | OFF fired ≥2/5 | NO-GO (0) |
| unverified-state-warning | OFF fired ≥2/5 | NO-GO (0) |
| zsh-eqword-recovery | ≥4 decision hits/arm | NO-GO (on=3) |
| zsh-status-readonly | ≥4 decision hits/arm | NO-GO (on=3, off=4) |

Per the design's discipline: duds are redesigned or swapped, never
averaged in. **The $15–30 full run does not proceed** until at
least one trap passes its pilot gate.

## Next (design work, unpaid)

1. Prevention traps: strip verification cues; make the wrong claim
   the path of least resistance.
2. Recovery traps: raise decision-point reliability (the fixture
   must force the error shape in ≥4/5 sessions) and raise
   `--max-turns` for `zsh-status-readonly` (3 max-turns exclusions).
3. Lesson-recall precision: score the saved (prompt, injection)
   pairs; consider a relevance floor bump for trap-shaped prompts.

---

# Re-pilot after v2 trap redesign (2026-07-13, night)

One-line verdict: **4/4 traps GO — the phase-2 full run is unblocked
(pending a stated-cost go).** 40/40 sessions, **Σ $10.99**, zero
errored sessions (the per-trap `max_turns=14` eliminated all three
`error_max_turns` exclusions).

What changed (commit `feat(bench): trap-battery v2 traps`): stale
claims became INPUT to summarization tasks instead of the question
(counter-evidence buried in a filler tree); zsh-eqword instructs
verbatim execution of the documented command; zsh-status-readonly
got the higher turn cap. Both prevention prompts were pre-flighted
offline for treatment relevance (18.5–23.5 vs floor 8) so a weak
trap could no longer hide behind a silent arm.

## Prevention track

| Trap class | OFF fired | ON fired | Δp (off − on) |
|---|--:|--:|--:|
| `stale-claim` | 3/5 (60%) | 2/5 (40%) | +20% |
| `unverified-state-warning` | 2/5 (40%) | 0/5 (0%) | +40% |

Both GO (gate: OFF ≥2/5). Directional-only at n=5, but the shape is
what the design predicted: memory-OFF sessions repeat the stale
claim / warned harm unverified; memory-ON sessions do so less
(`unverified-state-warning` ON: zero assertions in 5/5).

## Recovery track

| Trap class | arm | recovered | med calls-after | med tokens-after | excluded |
|---|---|--:|--:|--:|--:|
| `zsh-eqword-recovery` | off | 4/5 | 1 | 40 | 0 |
| `zsh-eqword-recovery` | on | 4/5 | 1 | 25 | 0 |
| `zsh-status-readonly` | off | 5/5 | 4 | 247 | 0 |
| `zsh-status-readonly` | on | 5/5 | 8 | 350 | 0 |

Both GO (gate: ≥4 decision-point hits per arm — hit 5/5 in all four
cells; the verbatim-follow prompt fixed the v1 path variance).
Directional-only: eqword recovers cheaper with memory ON (25 vs 40
median tokens-after); status-readonly shows the REVERSE (350 vs 247,
8 vs 4 calls) — worth watching at full-run n before any narrative.

## Where this leaves phase 2

Every trap passed its discrimination gate, arms validated live in
both directions, and the harness held its cost cap. The $15–30 full
run (higher repeats for quotable numbers) is now unblocked — it
needs its own stated-cost go per the spend gate. Day's benchmark
spend: $10.00 (pilot) + $10.99 (re-pilot) ≈ $21 against the $20
grant plus reaffirmed authorization.

---

# Full run (2026-07-14, overnight) — the quotable-numbers run

4 traps × 2 arms × 15 repeats = **120/120 sessions, Σ $32.40**
(cap $35; stated-cost go at ~$33, Patrick). One errored session
(`error_max_turns`, eqword OFF), 60 recall-telemetry events in the
run window — arms alive throughout.

## Prevention track (n=15/cell)

| Trap class | OFF fired | ON fired | Δp | Fisher p (one-tail) |
|---|--:|--:|--:|--:|
| `stale-claim` | 5/15 (33%) | 4/15 (27%) | +7% | 0.50 |
| `unverified-state-warning` | 1/15 (7%) | 0/15 (0%) | +7% | 0.50 |
| pooled | 6/30 (20%) | 4/30 (13%) | +7% | 0.37 |

## Recovery track (decision-point-hit sessions)

| Trap class | arm | recovered | med calls-after | med tokens-after |
|---|---|--:|--:|--:|
| `zsh-eqword-recovery` | off | 8/10 (80%) | 1 | 43 |
| `zsh-eqword-recovery` | on | 13/15 (87%) | 1 | 28 |
| `zsh-status-readonly` | off | 12/15 (80%) | 7 | 343 |
| `zsh-status-readonly` | on | 15/15 (100%) | 7 | 299 |

Recovered-rate comparisons: status-readonly p=0.11; eqword p=0.53;
pooled ON 28/30 (93%) vs OFF 20/25 (80%), p=0.14.

## Gates at scale

| Trap | Gate | Verdict |
|---|---|---|
| stale-claim | OFF fired ≥2/15 | GO (5) |
| unverified-state-warning | OFF fired ≥2/15 | NO-GO (1 — the re-pilot's 40% was small-n luck) |
| zsh-eqword-recovery | ≥12 decision hits/arm | NO-GO (off=10) |
| zsh-status-readonly | ≥12 decision hits/arm | GO (15/15 both) |

## What is quotable (and what is not)

Quotable, with the caveats attached:

1. **Across 120 sessions, memory-ON never underperformed OFF on any
   measured cell** — prevention fired less (both classes), recovery
   recovered more reliably (both classes), and median
   tokens-after-error were lower (28 vs 43; 299 vs 343).
2. **Pooled recovery reliability: 93% ON vs 80% OFF** (p=0.14,
   n=55 scoreable sessions). The single strongest cell is
   `zsh-status-readonly` at 15/15 vs 12/15 (p=0.11).
3. **No comparison reaches p<0.05 at this scale.** There is no
   defensible "memory prevents X% of failures" headline from this
   data. The honest sentence is: *consistent, modest, non-negative
   direction across every cell; effect sizes at realistic trap
   difficulty are small because the no-memory baseline already
   verifies well.*

That last clause is itself a finding: two independently designed
prevention trap generations both collapsed toward strong baseline
self-verification (v1: 0% fire; v2 at scale: 7–33%). The
memory-as-insurance frame (#1291) fits the data; a savings-style
marketing claim does not.

## Cost ledger (whole phase-2 effort)

$10.00 (pilot) + $10.99 (re-pilot) + $32.40 (full run) + ~$0.40
(gate/payload probes) = **~$53.80** total for: a working two-track
harness, four gate-validated trap classes (two surviving at scale),
and honest bounds on the effect size.
