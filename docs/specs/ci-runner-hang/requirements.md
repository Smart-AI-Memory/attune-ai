# Spec: CI Runner-Hang Root Cause and Fix

> The Ubuntu `coverage` and `test (ubuntu-latest, 3.12)` lanes
> intermittently freeze *inside the pytest execution step* and never
> progress until manually cancelled. The configured per-test timeout
> (`--timeout=60 --timeout-method=thread`) does not fire. Every QA
> session pays a cancel→rerun (and sometimes admin-merge) tax. This
> spec root-causes the hang and ships a fix plus a fast-fail guard so a
> future hang is self-documenting and auto-recoverable instead of a
> silent multi-minute stall.

**Status:** monitoring (see decisions.md D3, 2026-07-02)
**Created:** 2026-06-14
**Owner:** Patrick + agent
**Related:**

- `docs/specs/archive/windows-xdist-flakes/` — Windows xdist *worker-crash*
  family (opaque "worker 'gwN' crashed", passes on rerun). Same
  suspected polluter class (real socket/subprocess I/O in fixtures) but
  a different manifestation (crash on Windows vs hang on Ubuntu).
- `docs/specs/archive/ci-matrix-right-sizing/` — which lanes run (matrix
  sizing). Orthogonal: the hang is about a lane freezing, not about how
  many lanes spawn.
- `.claude/lessons.md` — "CI runner-hang recipe" (cancel→rerun, don't
  loop past ~2, escalate to admin-merge once the same-suite `coverage`
  job is green). This spec aims to retire the *need* for that recipe.

---

## Phase 1: Requirements

**Status:** shipped; spec in monitoring (D3)

### Problem statement

On `tests.yml`, the `coverage` and `test (ubuntu-latest, 3.12)` jobs
sometimes wedge: the test step starts, runs for 13+ minutes with zero
progress, and only ends when a human cancels it. Because two of the
seven required checks are affected, the PR sits `BLOCKED` and cannot
merge. The documented workaround (cancel the run, wait `completed`,
`gh run rerun --failed`) usually clears it, but it:

- requires a human to notice the stale `updatedAt` and intervene,
- recurs across reruns on the same PR (observed 2 hangs/PR this
  session), and
- breaks the unattended-QA model — the predictable infra failure lands
  exactly where autonomy needs a human (admin-merge authorization).

### Evidence (this session, 2026-06-14)

Captured from the cancelled first attempt of run `27485708268` (PR
#867) via `gh api .../attempts/1/jobs`:

| Step | Result | Duration |
|------|--------|----------|
| Set up job | success | ~2s |
| Checkout | success | ~2s |
| Set up Python 3.11 | success | ~7s |
| Install dependencies | success | ~20s |
| Check README badge freshness | success | ~68s |
| **Run tests with coverage** | **cancelled** | **13m32s, no progress** |

The `test (ubuntu-latest, 3.12)` job hung identically in its
**"Run tests"** step. Both runs in this session (#866, #867) hung;
each rerun of the *same* step then completed normally (coverage ~8 min,
test ~4 min). Prior session handoffs report the hang recurring "all
day" on 2026-06-13.

### Key facts that constrain the root cause

1. **The hang is in pytest execution, not infra/provisioning** — all
   pre-test steps complete in seconds; only the test step wedges.
2. **`pytest-timeout` is configured and did NOT fire.** Both lanes run
   `pytest -n auto --timeout=60 --timeout-method=thread`
   (`tests.yml:152` test, `tests.yml:198` coverage). A 60s per-test
   thread-timeout that never triggers during a 13-min hang means the
   wedge is **not a single test the thread method can interrupt** —
   consistent with a thread blocked in an uninterruptible C call while
   holding the GIL, or a wedge in the xdist controller↔worker channel
   that lives *outside* any single test's timeout window.
3. **Intermittent.** The identical step succeeds on rerun → a race /
   resource / I/O-dependent deadlock, not a deterministic bug.
4. **Not coverage-specific.** Both the `coverage` lane (pytest-cov) and
   the plain `test` lane hang, so `--cov` is at most an aggravator, not
   the cause.
5. **`-n auto` (xdist) is in play on both lanes**, and the sibling
   Windows spec already traced *worker crashes* to real
   socket/subprocess I/O in fixtures — a strong prior for the polluter
   class.

### Goals

- **G1 — Diagnose:** turn the next hang from opaque into a named stack
  trace (all-thread dump at the hang site).
- **G2 — Fast-fail guard:** a job-level hard timeout so a hang fails in
  ~bounded time and is auto-rerunnable, instead of running until manual
  cancel (or the GitHub 6h ceiling).
- **G3 — Root fix:** identify and fix the polluter (test/fixture) or
  the xdist/timeout configuration that allows an un-killable wedge.
- **G4 — Regression guard:** a guard that fails fast at authoring time
  if a test re-introduces the wedge condition (real I/O / un-timed
  blocking), so the class cannot silently return.

### Non-goals

- Matrix right-sizing (covered by `ci-matrix-right-sizing`).
- The Windows worker-crash inventory (covered by
  `windows-xdist-flakes`), except where a shared polluter is found —
  then fix once and cross-reference both specs.
- Eliminating `-n auto` / coverage outright (performance regression);
  only change them if proven causal and no narrower fix exists.

### Acceptance criteria (Done when)

- The next observed hang produces a full all-thread traceback in the CI
  log naming the wedged frame (G1 verified by a deliberately-injected
  hang in a throwaway branch, or by the first real hang post-merge).
- A job-level `timeout-minutes` guard is live on the `test` and
  `coverage` jobs, sized above the p99 normal runtime, so a wedge fails
  the job (not the whole run silently) and `rerun --failed` recovers it.
- Root cause is identified and fixed, OR — if not reproducible after a
  bounded investigation — the diagnostics (G1/G2) are shipped and the
  spec is left `monitoring` with the probe wired to catch the next
  occurrence. (Tar-pit guard: do not chase an unreproducible hang past
  two failed investigation attempts; ship the diagnostics and wait for
  a named stack.)
