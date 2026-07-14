# Decisions: CI Runner-Hang Root Cause and Fix

**Status:** monitoring (D3, 2026-07-02)
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

### D3 — Spec goes `monitoring`; cause is xdist/execnet-internal
(decided 2026-07-02)

The 4th captured hang (run `28566485306`, PR #1212) fired on
**windows-latest** — a spawn-only platform where the fork-Pool
fd-leak hypothesis is structurally impossible — with the same
end-of-session signature as the three Linux captures. This is the
stronger form of the tar-pit exit condition written into the
3rd-capture update: the cause is xdist/execnet-internal, not ours to
fix. Phase-1 deliverables (job `timeout-minutes` + hang-dump capture)
already bound the tax; recovery is `gh run rerun <id> --failed`.
The #1085 probe was additionally found blind on Windows (`/proc` +
GNU-ps assumptions); deliberately NOT building a Windows probe.
See `phase2-findings.md` "Phase 2 close-out" and
`evidence/run-28566485306/`.

**Reopen when:** a capture shows a test frame (not end-of-session),
or an adoptable upstream pytest-xdist/execnet fix appears.

---

## Resolved decisions (Patrick, 2026-06-14)

- **OD1 → own spec.** This stays a standalone spec, cross-linked to
  `windows-xdist-flakes`. If P3/P5 prove a *shared* polluter, fix once
  and reference both.
- **OD2 → tightened from 75.** `coverage` job → **25**; matrix `test`
  job → **35** (flat). *Implementation correction:* the first attempt
  used a per-OS `${{ matrix.os ... && 20 || 40 }}` expression, but that
  broke the existing `test_timeout_values_are_reasonable` guard (it
  expects an integer, got the expression string). A flat 35 passes the
  guard, stays generous for Windows/macOS (~13–15 min normal) to avoid
  false-fails, and still fails a wedged ubuntu step far faster than 75.
  Per-OS tightness is unnecessary anyway: the **early faulthandler dump
  (~10 min) is the diagnostic**; the job timeout is only the kill
  backstop. Re-tune after a week of observed durations.
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

---

## Phase 1 status + Phase 2 handoff (2026-06-14)

**Phase 1 DONE — PR #874** (`ci/runner-hang-phase1`): faulthandler
watchdog in `tests/conftest.py` (CI-gated, Linux 600s / else 1200s) +
`timeout-minutes` 75→ test 35 / coverage 25. Local smoke-verified
(watchdog dumps at threshold, test still passes; unset = not armed).
The guard-test break was fixed in the same PR (flat int, not a per-OS
expression). At handoff #874 is open with auto-merge — **confirm it
merged** (`gh pr view 874 --json state,mergedAt`).

### Phase 2 — start here, in a FRESH session

Phase 2 is **gated on a real hang stack**. Do NOT attempt a root fix
without one — guessing failed prior CI specs (see the "re-validate a
spec's premise" lesson). Concretely:

1. **Confirm Phase 1 merged** and the watchdog is live on `main`.
2. **Wait for the next hang.** With #874 live, a wedged ubuntu lane now
   (a) prints an all-thread faulthandler dump at ~10 min and (b) fails
   the job at 25–35 min instead of stalling. When CI shows a `test`/
   `coverage` job failing at/near its `timeout-minutes` (not a normal
   assertion failure), pull its log:
   `gh api repos/Smart-AI-Memory/attune-ai/actions/jobs/<job_id>/logs`
   (works once the JOB is complete even if the RUN is in progress) and
   find the `Timeout (0:..)!` section — it names the wedged frame(s) in
   the controller and each worker.
   - #874's OWN run is a full-matrix run (touches tests.yml), so it may
     itself capture a stack — check its run first.
3. **Classify with the stack:** a worker wedged in a C-level
   socket/subprocess/lock call ⇒ H1/H2 (the I/O-polluter family shared
   with `windows-xdist-flakes`); a coverage-combine frame ⇒ H3.
4. **Fix narrowly** (per design.md "Proposed fix shape"): mock/loopback
   the polluting I/O with an explicit socket timeout (proven Windows-
   spec pattern), and only then consider OD4 (`--timeout-method=signal`
   on POSIX) if the stack shows a C-call the thread method couldn't
   break. Land the P5 autouse I/O guard (G4) once H2 is confirmed (OD3
   says defer until then).
5. **Verify with a rerun count**, not a single green — intermittent bug
   ⇒ require ≥10 clean reruns under `-n auto` (design.md G3).

**If no hang reproduces within a reasonable window:** that's a fine
outcome — Phase 1's diagnostics + fast-fail already retire most of the
intervention tax. Mark the spec `monitoring` and let the next captured
stack reopen Phase 2. Tar-pit guard: do not chase an unreproducible
hang past two investigation attempts.

---

## D-2026-07-06: exit-139 split into its own tracked class

The 5th capture's tripwire (third exit-139 sighting) fired on run
`28806701681` (PR #1279) — and the capture also met the standing
reopen criterion (a test frame in a complete worker dump). Decision:

- **Split**, don't reopen: the exit-139 class now lives at
  `docs/specs/windows-exit139-segfault/` with a confirmed H1/H2
  mechanism (unit test → unmocked `UnifiedMemory` → live
  `getaddrinfo("localhost")` in redis-py `_connect`, not bounded by
  `socket_connect_timeout`) and a narrow fix plan per step 4 above.
- **This spec stays `monitoring`** for the original end-of-session
  wedge (captures 1–4): still no test frame, still unreproducible,
  tar-pit guard still applies.
- Rationale for the split over a reopen: the two shapes now have
  different mechanisms, different evidence quality, and different
  dispositions (fixable vs monitored) — one spec status can't honestly
  cover both.
