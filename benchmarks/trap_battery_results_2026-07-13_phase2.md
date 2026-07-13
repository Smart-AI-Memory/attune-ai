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
