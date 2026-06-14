# Decisions: CI Runner-Hang Root Cause and Fix

**Status:** draft
**Created:** 2026-06-14
**Requirements:** [requirements.md](requirements.md) ·
**Design:** [design.md](design.md)

---

## Decision log

### D1 — Diagnostics-first, not fix-first (decided 2026-06-14)

The hang is intermittent and opaque. Prior CI specs in this repo went
stale by hypothesizing a root cause and building probes around it
before the failure mode was confirmed (see the "re-validate a spec's
premise" lesson). So the first PR ships only diagnostics + a fast-fail
guard (P1 faulthandler dump + P2 `timeout-minutes`); the root fix waits
for a named stack trace from a real or injected hang.

**Why:** without a stack trace the root fix is guesswork; with one it is
mechanical.

### D2 — Job `timeout-minutes` ships regardless of root cause
(decided 2026-06-14)

Even before the cause is known, a bounded job timeout converts a silent
multi-minute (worst case 6h) wedge into a fast, visible, auto-rerunnable
failure. This alone removes most of the human-intervention tax the
"CI runner-hang recipe" lesson describes.

**Open:** exact `timeout-minutes` value — start at 25 (test p99 ~4 min,
coverage ~8 min; 2–3× headroom). Tune after observing a week of normal
runtimes.

---

## Open decisions (need Patrick or probe data)

- **OD1 — Is this its own spec or a phase of `windows-xdist-flakes`?**
  Recommendation: **own spec** (different OS, different manifestation —
  hang vs crash), cross-linked. If P3/P5 prove a *shared* polluter,
  fix once and reference both. Confirm.
- **OD2 — Acceptable normal-runtime ceiling for the timeout guard.**
  Need a week of `coverage`/`test` durations to set `timeout-minutes`
  without false-failing healthy slow runs. Proposed interim: 25 min.
- **OD3 — Appetite for the P5 autouse I/O guard now vs after a
  confirmed H2.** It is the durable G4 regression guard but touches the
  whole unit-test tree (some legitimate loopback tests must be
  allow-listed). Recommend deferring until P1/P3 implicate H2, to avoid
  a large speculative change.
- **OD4 — `--timeout-method=signal` on POSIX lanes (P4).** Only pursue
  if P1's stack shows a C-call wedge the thread method missed; do not
  blind-switch (xdist interaction risk).

---

## Phase plan (proposed)

| Phase | Scope | PR shape |
|-------|-------|----------|
| 1 | P1 faulthandler all-thread dump + P2 job `timeout-minutes` | one `ci(tests)` PR; validate G1/G2 with an injected hang on a throwaway branch |
| 2 | Wait for a named stack (real hang or injected); P3 serial bisect if needed | investigation note in this spec dir |
| 3 | Root fix per confirmed hypothesis (H2 polluter fix / H3 coverage isolation) + G4 guard | `fix(...)` PR with a rerun-count verification |
| 4 | Promote `clock-tz`-style: if a diagnostic lane was added, fold it back or remove | cleanup PR |

Phase 1 is self-contained and worth shipping immediately; Phases 2–4
are gated on Phase 1's diagnostics producing a stack.
