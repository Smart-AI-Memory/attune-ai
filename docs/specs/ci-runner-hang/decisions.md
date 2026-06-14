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

## Resolved decisions (Patrick, 2026-06-14)

- **OD1 → own spec.** This stays a standalone spec, cross-linked to
  `windows-xdist-flakes`. If P3/P5 prove a *shared* polluter, fix once
  and reference both.
- **OD2 → 25 min interim.** `timeout-minutes` tightened from the
  current 75. Implementation: coverage job → 25; matrix `test` job →
  20 on ubuntu (where the hang lives, normal ~4 min) / 40 on
  Windows+macOS (normal ~13–15 min, must not false-fail). Re-tune after
  a week of observed durations.
- **OD3 → defer.** The broad P5 autouse I/O guard waits until P1/P3
  implicate H2 — no large speculative change now.
- **OD4 → approved, gated.** Pursue `--timeout-method=signal` on the
  POSIX lanes *only after* Phase 1's stack shows a C-call wedge the
  thread method missed. Not a blind switch (the existing tests.yml
  comment notes thread-method is deliberate for Windows; signal is
  POSIX-only and has xdist-interaction risk).

## Implementation note (Phase 1)

faulthandler is armed in `tests/conftest.py` gated on the auto-set `CI`
env var (so local runs are unaffected) with an OS-tuned threshold
(`RUNNER_OS == "Linux"` → 600s, else 1200s), via
`faulthandler.dump_traceback_later(secs, repeat=False)` at conftest
import time so it covers the xdist controller AND every worker
subprocess, including collection-time hangs.
(`dump_traceback_later` always dumps ALL threads — there is no
`all_threads` kwarg on it; that exists only on `register()` /
`dump_traceback()`. Passing it raises `TypeError` at import and breaks
collection — caught by the Phase 1 local smoke test before ship.) The
threshold sits below the job `timeout-minutes` so the all-thread stack
lands in the log *before* the fast-fail kills the job. Shipped in #874. Threshold overridable for local
smoke-testing via `PYTEST_HANG_DUMP_SECONDS`. This keeps the `tests.yml`
diff to the two `timeout-minutes` lines (no `env:` edits → no conflict
with the open `--cov-fail-under` change in #871).

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
