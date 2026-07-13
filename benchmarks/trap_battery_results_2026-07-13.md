# Trap battery — phase 1 pilot results (2026-07-13)

**Run:** 3 traps × 2 arms × 5 repeats = 30 headless sessions, all ok
(0 errors). Executed by Patrick from a plain terminal on branch
`feat/trap-battery-pilot`; live terminal transcript is the source of
record for this doc. Total spend ≈ **$5.65** (vs the $30–60
estimate). **PILOT scale — nothing below is quotable externally; the
20+/cell rate run is where numbers earn quotes.**

## Fired rate by class and arm

| Trap class | OFF fired | ON fired | Δp (off − on) |
|---|--:|--:|--:|
| `zsh-eqword` | 2/5 (40%) | 0/5 (0%) | **+40%** |
| `git-commit-verify-landed` | 0/5 (0%) | 0/5 (0%) | +0% |
| `question-shape` | 5/5 (100%) | 4/5 (80%) | +20% |

Output is failure rates and Δp only — no savings claim (insurance
frame, #1291 discipline).

## Discrimination receipts

Gate: a trap earns phase 2 by firing ≥2/5 in the OFF (lesson-absent)
arm.

- **`zsh-eqword` — receipt obtained.** OFF repeats #2 and #3 fired
  with tool-result evidence `zsh:1: == not found` (the exact
  signature verified live before the regex was written). ON arm:
  0/5 — every memory-on session quoted the separator.
- **`question-shape` — receipt obtained, but see verdict.** OFF
  5/5, all with prose either/or evidence (e.g. *"Which scope do you
  want to ship — Minimal or Full?"*). The ON arm ALSO fired 4/5 —
  the surfaced rule barely changes behavior.
- **`git-commit-verify-landed` — no live receipt.** 0/5 OFF. The
  scorer itself is receipt-proven on canned transcripts (unit
  tests), but the live trap never fired: baseline sessions handled
  the hook's visible exit-1, re-staged, retried, and verified. The
  fixture's failure is louder than the lived original (`git commit
  -q` exiting 0 with the commit silently skipped), which a plain
  pre-commit hook cannot reproduce — hooks that exit 0 let the
  commit proceed.

## Class verdicts (phase-2 go/no-go)

- **`zsh-eqword`: GO.** Discriminates at exactly the gate (2/5 OFF)
  with a pilot Δp of +40% and a clean prevention story (ON 0/5).
  Graduates to the 20+/cell rate run.
- **`git-commit-verify-landed`: NO-GO as designed — redesign or
  swap.** The trap tests recovery from a *visible* failure, which
  current baseline behavior already handles. Either find a faithful
  reproduction of the silent-skip (hard: needs the real pre-commit
  framework's stash dance) or swap in `stale-claim` (pre-approved
  candidate, requirements §swap).
- **`question-shape`: SWAP, with a finding worth keeping.** It
  passes the OFF-gate trivially (5/5) but ON≈OFF means the lesson
  is either not being injected in fixture-repo sessions or is
  injected and ignored — the current harness can't distinguish
  these. Swap in `zsh-status-readonly` for phase 2 (pre-approved),
  and carry the harness follow-up below.

## Findings beyond the table

1. **First measured Δp > 0 for the memory suite.** zsh-eqword is
   the first behavioral (not cost) evidence that a surfaced lesson
   prevents a lived failure class. Pilot-labeled, n=5/cell.
2. **Failure has a visible cost signature.** The two OFF-arm
   zsh firings ran ~13s / ~$0.18 vs ~8s / ~$0.15 for clean runs —
   the error-and-recover loop costs ~60% more wall and ~20% more
   spend even on a toy task. This is the insurance premium's
   counterpart measured on the benefit side.
3. **Harness follow-up (phase 2): injection detection.** Record
   per-session whether the recall hooks actually injected content
   (visible in the stream-json system/context events), so
   "lesson ignored" and "lesson never surfaced" stop being
   confounded — question-shape's ON 4/5 is uninterpretable without
   it.
4. **Cost model correction.** ~$0.19/session mean → a 20/cell rate
   run for two classes ≈ 80 sessions ≈ **$15**, well under the
   phase-2 assumptions.
