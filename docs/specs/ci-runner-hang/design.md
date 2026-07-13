# Design: CI Runner-Hang Root Cause and Fix

**Status:** closed (2026-07-02) — D3/PR #1213: cause is xdist/execnet-internal, not ours to fix; Phase-1 diagnostics shipped (#874: hang dump + job timeouts); passive monitoring with reopen criteria in decisions.md; exit-139 class split to windows-exit139-segfault (2026-07-06)
**Created:** 2026-06-14
**Requirements:** [requirements.md](requirements.md)

---

## Approach

Diagnostics-first. The hang is intermittent and currently opaque, so
the highest-leverage move is to make the *next* occurrence
self-documenting and bounded, then let the named stack drive the root
fix. Ship G1 (hang dump) and G2 (job timeout) before attempting G3
(root fix), because without a stack trace the root fix is guesswork —
and guessing failed the "re-validate the premise" test in prior CI
specs.

## Ranked hypotheses

**H1 — xdist worker/controller wedge the thread-timeout can't break
(most likely).** A worker blocks in an uninterruptible C call (socket
recv, subprocess wait, lock acquire) while holding the GIL, so
`--timeout-method=thread` (which raises in the worker's main thread)
can never run. The controller then waits on that worker indefinitely.
Fits all five constraints: in-test-step, timeout doesn't fire,
intermittent, both lanes, `-n auto`. Shared polluter class with the
Windows worker-crash spec.

**H2 — A specific test doing real network/subprocess I/O without its
own timeout** (subset of H1's mechanism). The Windows spec already
found three such sites in the memory/agents test trees (real Redis
subprocess starts, non-loopback socket probes). On Ubuntu the same code
may *hang* (connect to a black-hole host that neither refuses nor
resolves quickly) rather than crash. Strong prior.

**H3 — pytest-cov × xdist data-collection deadlock at the
worker/process boundary.** Coverage combines per-worker data at
teardown; a worker wedged mid-collection could stall combine. Weakened
by the plain `test` lane also hanging, but `--cov` may widen the race
window — keep as an aggravator to rule out, not a primary.

**H4 — Runner resource exhaustion (memory → swap thrash).** A test
allocating unbounded objects (the handoff notes a historical "~100k
MagicMocks zombie thread") could make the runner thrash and appear
hung. Less likely (pre-test steps fine, rerun fine), but `faulthandler`
+ a memory probe will show it if real.

## Probes (cheap-first; STOP when a named stack appears)

**P1 — faulthandler all-thread dump (the keystone diagnostic).**
Enable a watchdog that dumps *every* thread's stack to stderr after N
seconds, so a hang prints where it is wedged — in the worker AND the
controller. Two complementary mechanisms:

- pytest `faulthandler_timeout` in config (dumps the main process), and
- `PYTHONFAULTHANDLER=1` plus an explicit
  `faulthandler.dump_traceback_later(<sec>, all_threads=True)` armed in
  a session-scoped conftest fixture so worker subprocesses are covered.

Set the dump threshold below the job timeout (e.g. 300s) so the trace
lands *before* the fast-fail kills the job. Validate by injecting a
deliberate `time.sleep(9999)` test on a throwaway branch and confirming
the CI log names it.

**P2 — job-level `timeout-minutes` (the mitigation, ships regardless).**
Add `timeout-minutes:` to the `test` and `coverage` jobs in
`tests.yml`, sized at ~2–3× p99 normal runtime (normal: test ~4 min,
coverage ~8 min → start at 25 min). A wedge then fails that job in
bounded time; `gh run rerun --failed` recovers it, and the failure is
visible instead of silent. Combined with P1, the failed job carries the
stack.

**P3 — serial bisect lane (confirm xdist involvement).** On a
diagnostic branch, run one lane with `-p no:xdist` (serial). If the
hang vanishes serially across several runs, xdist is implicated (H1).
If it still hangs serially, the wedge is in a test's own blocking I/O
(H2) independent of xdist.

**P4 — switch `--timeout-method` on POSIX.** Try `--timeout-method=
signal` on the Ubuntu lanes (signal-based SIGALRM can interrupt some C
calls the thread method cannot). If the per-test timeout then *fires*
and names the test, that both diagnoses and partially mitigates. Caveat:
signal method interacts poorly with some xdist setups — gate behind P1's
findings, do not blind-switch.

**P5 — I/O polluter inventory (if P1/P3 point at H2).** Extend the
Windows spec's proposed `autouse` guard to the whole unit tree: a
session fixture that fails fast on (a) real `ensure_redis`/subprocess
starts and (b) socket connects to non-loopback hosts. This both finds
the current polluter and becomes G4's regression guard.

## Proposed fix shape (driven by probe results)

1. **Always ship (diagnostics + mitigation):** P1 faulthandler dump +
   P2 job `timeout-minutes`. Low risk, high value, independent of root
   cause. This alone retires most of the human-intervention tax.
2. **If H2/H1 confirmed:** fix the polluting test (mock the I/O / use
   loopback + closed port + an explicit socket timeout, per the Windows
   spec's proven pattern) and land P5's autouse guard (G4).
3. **If H3 confirmed:** isolate coverage combine (e.g. `--cov-context`
   off, or `COVERAGE_CORE=sysmon` on 3.12+) — narrowest change first.
4. **If unreproducible after 2 attempts:** ship 1+2, mark the spec
   `monitoring`, and let the next named stack reopen G3. (Tar-pit
   guard.)

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `timeout-minutes` set too low fails healthy slow runs | medium | size at 2–3× p99; the badge/dep steps are outside the test step so only test time counts |
| faulthandler dump noise on every run | low | only dumps on the timer; threshold > normal runtime so healthy runs never trigger |
| signal timeout-method breaks xdist | medium | P4 is gated behind P1, not blind |
| Fixing one polluter while another lurks (cf. Windows spec needing 3 fixes) | medium | land the P5 autouse guard so the *class* is caught, not just instances |
| Changing `tests.yml` triggers the full matrix (D2 path) | low | expected; validates the change on all lanes |

## Verification

- **G1:** inject a deliberate hang on a throwaway branch → confirm the
  CI log prints the all-thread stack naming the injected frame.
- **G2:** same injected hang → confirm the job fails at
  `timeout-minutes`, not at manual cancel, and `rerun --failed`
  recovers.
- **G3:** after the fix, the named polluter's test passes serially and
  under `-n auto` across ≥10 reruns (intermittent bug → require a run
  count, not a single green).
- **G4:** add a test that performs the wedge condition and assert the
  autouse guard fails it fast.
