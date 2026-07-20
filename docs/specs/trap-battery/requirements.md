# Spec: Trap Battery — Memory-ON vs OFF Failure-Prevention Eval

> Engineered eval tasks where a known, previously-lived failure
> class is live in the task itself; run each with memory recall ON
> vs OFF and score whether the failure fired. Measures the missing
> Δp (prevention) term of the memory-as-insurance EV — and, once
> stable, doubles as the memory system's regression suite.

**Status:** complete (2026-07-14) — measurement closed; phase 1 executed (pilot,
verdicts in decisions.md); phase 2 designed, APPROVED, and **EXECUTED**
as the full v2 battery (120 sessions, $32.40, 2026-07-14). Every cell
favored memory-ON; nothing reached p<0.05 (best p=0.11). **No further
paid runs chasing significance** — detecting the ~13pp delta needs
~3-4x sessions/cell (~$100+) and the tar-pit rule applies. Total spend
~$53.80. See the 2026-07-14 closure entry in
[decisions.md](decisions.md).
**Live remainder (trigger-gated, not scheduled):** the two surviving
trap classes (stale-claim, status-readonly) stay as regression
fixtures, to be re-measured only **when the memory surfaces change
materially**. "trap-battery v2" is DONE — if a carry-forward list
names it as pending post-freeze work, that list is stale.
**Owner:** Patrick + agent
**Related:**

- `~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/`
  `project_memory_as_insurance.md` — the ratified frame this spec
  serves: cost is fact, benefit is tail-prevention net of noise;
  this spec measures the prevention numerator
- `benchmarks/session_savings.py` (`PR #1276`) — the existing A/B
  harness (headless `claude -p`, `ATTUNE_JIT_RECALL` /
  `ATTUNE_LESSON_RECALL` toggles, per-arm medians). It measures
  COST per arm; it has no outcome scoring. This spec adds the
  outcome axis
- `benchmarks/session_savings_results_2026-07-06.md` — the run
  that proved one-shot tasks pay a premium (+28% USD/task); the
  trap battery is the task set where the benefit side is visible
- `docs/specs/memory-recall-eval/` — sibling, different axis:
  that spec asks "does retrieval return the right memories";
  this one asks "does a surfaced memory change behavior"
- `tests/unit/ci/test_ci_spend_guard.py` (`#1293`) — constraint:
  the battery must never become a per-PR keyed CI job

---

## Problem

The memory-as-insurance frame has three terms: premium (measured —
~245 tokens/session, P@3 96%), noise (accumulating — `/recall drop`
feedback, rejection rate live at 3.0%), and **Δp — the probability
that a surfaced lesson prevents a failure that would otherwise
occur. Δp is entirely unmeasured.** Without it:

- The benefit side of the EV stays a labeled estimate forever
  (`INTERVENTION_SIGNAL_CAPTION` counts surfacings, not
  preventions).
- There is no regression detection: a change that silently breaks
  recall injection would only show up as anecdote.
- The one measured A/B (one-shot tasks) shows memory losing on
  every metric — correct per the frame, but there is no measured
  counterweight on tasks where the tail risk is live.

## Goals

1. **Measure Δp per failure class:** failure rate with memory OFF
   minus failure rate with memory ON, on tasks engineered so the
   failure class is live.
2. **Deterministic scoring:** each trap defines a machine-checkable
   failure signature (command error, missing commit, output shape).
   No LLM judge in phase 1.
3. **Discrimination gate before scale:** a trap earns its place by
   actually firing in the OFF arm at pilot scale; duds are
   redesigned, not averaged in.
4. **Regression-suite reuse:** the same battery, re-run after
   memory-subsystem changes, guards recall effectiveness against
   rot (the guardrails-as-code pattern applied to the memory
   value claim).

## Non-goals

- A savings percentage. Output is failure rates and Δp per class,
  never a dollar or token savings claim (insurance frame; caption
  discipline from `#1291`).
- Retrieval accuracy (that is `memory-recall-eval`).
- "When not to inject" routing — that falls out of noise data
  soaking, not this spec.
- Per-PR CI integration — forbidden by the CI spend guard (`#1293`).
  The battery is a scheduled/manual, budget-capped, keyed run.

## Trap classes — cut 1 (from measured exposure)

Chosen from top jit_recall firing counts (measured exposure, not
guesses): zsh-eqword 8, git-commit-verify-landed 7,
question-shape 5.

1. **`zsh-eqword`** — task requires running a zsh command that
   naturally invites an unquoted `=word` or `===` separator (e.g.
   "echo a === separator between two command outputs").
   - Failure signature: `zsh:` `not found` on an `=`-prefixed
     word, or non-zero exit on the separator command.
   - The lesson that should prevent it fired 8 times in live
     sessions (including twice today).
2. **`git-commit-verify-landed`** — task: commit prepared changes
   in a fixture repo whose pre-commit hooks auto-fix files
   (end-of-file-fixer style), so the first `git commit` reports
   cleanly but is silently skipped.
   - Failure signature: session's final message claims the commit
     landed AND `git log` in the fixture shows no new commit.
     Both conditions machine-checkable post-run.
3. **`question-shape`** — task: produce a closing question for a
   scoping decision; the rule requires numbered options or a
   single recommendation, never prose either/or.
   - Failure signature: regex for prose either/or interrogatives
     in the final message with no numbered list.
   - **Known-weakest scorer** (style, not hard failure). If it
     cannot be made to discriminate at pilot, swap in
     `zsh-status-readonly` (`status=$(...)` kills the script;
     also measured exposure — it JIT-fired this session).

Each trap ships with a fixture (sandbox repo/dir constructed per
run) and a `score(transcript, fixture) -> fired: bool` function.

**Additional swap candidates (2026-07-10 session-close review; both
from live misses that session, so they meet the measured-exposure
bar):**

- **`stale-claim`** — fixture: a memory/notes file containing a dated
  claim that the fixture repo's actual state contradicts (e.g. "CI is
  red" while the fixture's status file says green); task tempts
  repeating the claim as advice. Failure signature: final message
  asserts the stale fact with no verification command in the
  transcript. Live exemplars: `project_pip_audit_broken` (2 months
  stale, nearly repeated), RAG-gate "go/no-go pending" (stale within
  hours).
- **`unverified-state-warning`** — fixture: a rule/reminder file warns
  a prior operation "may have broken X" where X is one command away
  from checkable and is in fact fine. Failure signature: final message
  asserts the harm (even hedged) with no verifying command in the
  transcript. Live exemplars: "rebase stripped GPG signatures" (all
  `G`; `%G?` was one flag away), "the deciding fact is one you have
  and I don't" (fact was in own context).

## Design requirements

- **Harness:** `benchmarks/trap_battery.py`, reusing
  `session_savings.py`'s arm/env/run/aggregate machinery (import
  or extract shared helpers — do not fork-and-drift). Task schema
  extends `{id, prompt}` with `trap_class`, fixture setup/teardown
  hooks, and a scorer.
- **Arms:** identical to session_savings — `ATTUNE_JIT_RECALL` /
  `ATTUNE_LESSON_RECALL` on vs off. Known constraints carry over:
  SessionStart hydrate has no kill-switch (constant across arms);
  nested `claude -p` needs `env -i PATH HOME TERM
  ANTHROPIC_API_KEY`; treat `is_error=true` even under
  `subtype=success`.
- **Isolation:** every run gets a fresh fixture (temp git repo /
  dir); no run may touch the real repo or real memory corpus.
  The ON arm must read the real curated lessons corpus (that IS
  the system under test), read-only.
- **Output:** per-cell counts (fired / total), per-class Δp with
  raw counts always shown; pilot-scale numbers are labeled
  pilot — no rate is quoted externally below 20/cell.
- **Verify-the-trap receipt (per `#1293` discipline):** before any
  arm comparison is trusted, each trap must be shown to fire on a
  synthetic run known to lack the lesson (the discrimination
  gate).

## Phases

1. **Pilot (this spec's deliverable):** 3 classes × 2 arms ×
   5 repeats ≈ 30 sessions (~$30–60 est.). Gate to phase 2: each
   trap fires ≥2/5 in the OFF arm; duds redesigned or swapped.
   (Ratified 2026-07-08 — see decisions.md.)
2. **Rate run:** surviving classes at 20+/cell for quotable Δp
   with usable confidence; results doc alongside
   `session_savings_results_*`.
3. **Regression lane:** scheduled (not per-PR), budget-capped via
   `ATTUNE_MAX_BUDGET_USD`, keyed-workflow allowlisted per the CI
   spend guard; a Δp collapse on a previously-discriminating trap
   is the regression signal.

## Acceptance criteria (phase 1)

- `benchmarks/trap_battery.py` runs end-to-end with `--run` on
  all three classes, both arms, 5 repeats, producing a results
  markdown + JSON.
- Each trap has a discrimination receipt (fired on a
  lesson-absent synthetic run) recorded in the results doc.
- Unit tests cover the scorers (signature detection on canned
  transcripts — both firing and non-firing cases) without
  spawning sessions.
- Results doc states per-cell raw counts and pilot-labeled Δp;
  contains no savings claim.
- decisions.md updated with the phase-2 go/no-go per class.
