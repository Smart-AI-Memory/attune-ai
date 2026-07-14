# Decisions — CI gating-lane isolation

**Status:** superseded (2026-06-17) — reconciled at 2026-07-14 triage (was: draft)

Append-only log. See `requirements.md` for the problem framing.

---

## Context that motivated the spec (2026-06-15)

Opened after QA #6 (the omit-audit conversion run) where the
runner-hang on the `coverage` and `clock-tz`/Windows lanes blocked
auto-merge on nearly every PR (#892–#894, #901, #904), each needing
manual `gh run cancel` / `gh run rerun --failed` and, on #904, an
admin-merge on a hung `coverage` (justified by `test (ubuntu 3.12)`
being green — same suite — and the diff being coverage-only-additive).

The pre-existing `auto-merge-safe.yml` D7 retry fix (this session)
handles the *concurrent-merge race* but NOT the *hang-blocks-trigger*
problem — that needs the topology change proposed here.

## Resolved decisions

- **D1 — layering order. RATIFIED (2026-06-15): A → B → C.** Layer A
  (step-level timeout + bounded in-run retry on the gating lanes)
  shipped first as the cheapest, self-contained relief. B (gate/matrix
  topology split) and C (coverage shard) remain deferred and only get
  built if measurements after A still show merge friction.
- **D2 — retry mechanism. RESOLVED (2026-06-15): pure-shell re-invoke.**
  Chose a `timeout`-wrapped bash retry loop over `nick-fields/retry`.
  Rationale: (a) no new third-party action / SHA-pin / supply-chain
  surface (consistent with ci-matrix-right-sizing's "no third-party
  action" preference and this repo's SHA-pin + scorecard posture);
  (b) full control over the retry predicate — we retry **only** on the
  step `timeout`'s rc=124 (the runner-hang signature) and return any
  other non-zero immediately, so a genuine red is never masked green
  (`nick-fields/retry` retries on any non-zero by default). Verified
  the five exit paths (clean / real-fail / hang→pass / hang→hang /
  hang→real-fail) behave correctly before shipping.

## Layer A — as-built (2026-06-15, PR pending)

- **Scope:** the two REQUIRED ubuntu gating lanes in `tests.yml` —
  `coverage` and `test (ubuntu-latest, 3.12)`. The `test` retry is
  Linux-gated (`runner.os == Linux`): `timeout` there is coreutils;
  on Windows `shell: bash` it resolves to the unrelated `timeout.exe`,
  and the macOS/Windows lanes are advisory, so they keep the plain
  invocation. `clock-tz` (advisory) was deliberately left out — a hung
  advisory lane blocking the *trigger* is failure-shape #1, which is
  Layer B's (topology) job, not A's.
- **Step timeout = 14m.** Sits ABOVE the 600s conftest hang-watchdog
  (so a wedged attempt still dumps its all-thread stack to
  `hang-dumps/` before the kill) and BELOW the job timeout (the
  all-attempts-hung backstop).
- **Job-timeout change:** `coverage` 25 → 40 to fit 2×14m attempts +
  pip-install/badge/codecov overhead (still ≤ the guard's 75 ceiling).
  `test` stays 35 (2×14m + overhead ≈ 31 fits). The job timeout is now
  the *final* backstop, not the first kill — the step `timeout` is the
  fast-kill. This re-loosening of `coverage` is consistent with, not a
  reversal of, the ci-runner-hang 75→25 tighten: that tighten existed
  to bound a *single* wedged attempt; Layer A now bounds the attempt at
  the step level (14m) and the job timeout only bounds the worst case
  of *both* attempts hanging.
- **Known limitation (accepted for v1):** `timeout` signals the pytest
  controller; on SIGKILL, orphaned xdist workers could in principle
  linger into the retry attempt. The observed hang freezes ~1s after
  start (before workers do real work), so this is low-risk; if
  measurements show retry-interference, escalate to a process-group
  kill (`setsid`) or Layer C. Recorded so a future hang isn't
  misdiagnosed.

## Still open

- **D3 — branch-protection migration.** Only relevant to Layer B (the
  topology split renames check contexts). Untouched by Layer A, which
  keeps every check in `Tests` under its existing name. _Deferred with
  Layer B._
