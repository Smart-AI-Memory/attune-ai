# Phase 2 Findings: CI Runner-Hang

**Status:** in progress (diagnostics hardened; root fix gated on a
captured frame)
**Created:** 2026-06-14
**Requirements:** [requirements.md](requirements.md) ·
**Design:** [design.md](design.md) ·
**Decisions:** [decisions.md](decisions.md)

---

## Summary

Phase 1 (#874) armed a `faulthandler` watchdog but a fresh forensic
capture on 2026-06-14 showed it had a gap: under xdist the dump fired
inside the wedged *worker* and was lost when the job was killed, so we
still had no frame. Phase 2 (this PR) closes that gap — the watchdog
now writes each process's all-thread stack to a per-worker FILE that an
`if: always()` CI step cats and uploads as an artifact, so a worker
dump survives the `timeout-minutes` kill. The root fix (the polluting
fixture/test) stays gated on a real captured frame per D1.

---

## Forensic capture — the hang's SHAPE

From the `coverage` job of run `27488685349` (PR #876,
`qa/analytics-commands`), killed at its 25-min timeout 05:14:34Z:

- The full suite (`-n auto`, workers gw0–gw3, Linux) reached **99% at
  04:54:29Z — only ~3.5 min in** — then froze for ~20 minutes (only
  30-second `[mem-tick]` heartbeats, no test output) until the kill. A
  real deadlock, not slowness.
- Memory was **flat at ~3.2 GB** the entire freeze (`avail ~12.8 GB`) —
  rules out OOM / memory leak (H4). A pure lock / uninterruptible-I/O
  deadlock.
- **Worker gw0 went silent FIRST**: its last output was
  `[gw0] [ 89%] PASSED .../test_base_dataclasses.py::TestCostReport::
  test_cost_report_default_cache_stats` at **04:53:56Z**. Workers
  gw1/gw2/gw3 then drained their queues to 99% (last `[gw2]` at
  04:54:29Z) and the session hung.

This is a classic **xdist controller deadlock**: gw0 wedged mid-test,
the other workers emptied their queues, and the controller waits
forever for gw0 to report → the session never completes. Confirms
hypothesis **H1** (design.md). The wedged test is the one gw0 picked up
*after* its last PASSED (in/after
`tests/unit/workflows/test_base_dataclasses.py`); the plain CI log only
tags *completions* with `[gwN]`, never the in-flight test, so the exact
gw0 test is not in the log — it must be reproduced.

---

## The Phase 1 watchdog GAP (root cause of "still no frame")

Phase 1 armed
`faulthandler.dump_traceback_later(secs, repeat=False)`, which defaults
to `file=sys.stderr`. No dump appeared in the captured log even though
the process was frozen 04:54→05:14 — well past the 600 s Linux trigger
(which would fire ~05:01).

**Why:** with pytest-xdist, `conftest.py` is imported in *each* worker
subprocess, so the timer that matters fires inside the wedged worker
(gw0). execnet does **not** forward a worker's raw fd-2 dump to the
controller's stdout on a hang — worker output is surfaced via its own
channel, typically flushed only at a test boundary/failure. So the
dump was written to gw0's local stderr and discarded when the job was
killed. The controller's own dump (had it fired) would have shown only
the queue-wait, not the wedged frame.

---

## The fix (this PR) — make the worker dump survive

Chose **option (a)** from the handoff (the robust one):

1. **`tests/conftest.py`** — the watchdog now opens
   `hang-dumps/hang-<worker>.txt` (keyed by `PYTEST_XDIST_WORKER`;
   controller → `hang-controller`) and passes it as `file=` to
   `dump_traceback_later`. The dir is workspace-relative (portable
   across Linux/macOS/Windows lanes), the file ref is kept in a module
   global so the fd stays alive, and the whole block is wrapped so an
   un-writable workspace falls back to the Phase 1 stderr behavior
   rather than breaking conftest import (which would fail *every*
   test). faulthandler writes via the raw fd (async-signal-safe), so
   the bytes hit the OS immediately — no buffer-flush concern; an
   `[hang-watchdog] armed: …` line is printed at arm time for
   correlation.

2. **`.github/workflows/tests.yml`** — the `test` and `coverage` jobs
   (the two `-n auto` lanes where the hang was observed) gained two
   `if: always()` steps: "Surface hang-watchdog dumps" (cats every
   non-empty dump into a `::group::`, prunes empty armed-but-never-
   fired files) and "Upload hang-watchdog dumps" (uploads `hang-dumps/`
   as a uniquely-named artifact, `if-no-files-found: ignore`). Because
   the dump fires at ~10 min and the job is killed at 25/35 min, the
   file is on disk before the kill and `if: always()` runs the capture
   after the test step is cancelled.

3. **Regression guard** — `tests/unit/ci/test_workflow_yaml.py::
   TestHangDumpCapture` fails if either lane loses its
   `if: always()` hang-dumps upload, so the gap can't silently reopen.

4. **`.gitignore`** — `hang-dumps/` (CI artifact only; never committed).

### Verification (G1, local)

Injected hang reproduced the mechanism end-to-end:
`CI=1 PYTEST_HANG_DUMP_SECONDS=3 pytest <hanging tests> -n 2`. Result:
`hang-dumps/hang-gw0.txt` named the **exact wedged frame**
(`test_hang.py line 3 in test_hangs`); `hang-controller.txt` showed the
xdist `dsession.loop_once` queue-wait — the same deadlock shape as the
forensic capture; non-hanging / respawned workers left empty files
(pruned before upload). This is the frame Phase 1 lost.

---

## Follow-up (deliverable #2 — gated, NOT in this PR)

Per D1 (diagnostics-first) and the tar-pit guard, the root fix waits
for a real captured frame. Once the next ubuntu hang uploads a
`hang-dumps-*` artifact (or `py-spy dump --pid <hung worker>` names it):

1. Reproduce locally under load to re-wedge gw0:
   `pytest tests/unit/workflows/test_base_dataclasses.py tests/workflows/
   -n 4 -p no:cacheprovider` in a loop (or the whole suite `-n 4`),
   watching for the 99%-freeze.
2. Classify the frame: a worker blocked in uninterruptible I/O
   (`socket.recv`, `subprocess.wait/communicate`, a lock `.acquire()`
   inside a fixture) ⇒ H1/H2 — the same polluter family as
   `windows-xdist-flakes` (real socket/subprocess I/O in a fixture,
   hang-on-Linux vs crash-on-Windows).
3. Fix the polluting fixture/test: make the I/O hermetic / properly
   torn down (close sockets, terminate subprocesses, timeout on
   `.wait()`), per the proven Windows-spec pattern.
4. Land the P5 autouse guard (G4) that fails fast if a test opens a
   real socket or spawns a real subprocess (OD3 says defer until H2 is
   confirmed — now unblocked once a frame lands).
5. Verify with a **rerun count** (≥10 clean `-n auto` reruns), not a
   single green — the hang is nondeterministic / worker-distribution-
   dependent (the same PR's required `test (ubuntu-latest, 3.12)` lane
   PASSED while `coverage` wedged).

### Watch-outs

- `pytest-timeout`'s `--timeout=60 --timeout-method=thread` does NOT
  fire on this GIL-blocked / uninterruptible wedge — do not expect it.
- A clean run does not mean it's fixed; reproduce deliberately.
- Keep the watchdog threshold (Linux 600 s) below every lane's normal
  full-suite runtime so a slow-but-fine run never trips a false dump;
  tune via `PYTEST_HANG_DUMP_SECONDS` if normal runtimes climb.
- `clock-tz` also runs `-n auto` on ubuntu and could wedge; it was left
  out of the capture steps to keep this PR scoped to the two
  required-check lanes. Add the same two steps there if it ever hangs.

---

## Phase 3 — FIRST captured production frame (2026-06-15)

The Phase 2 dump-survival mechanism paid off: PR #911's `coverage`
lane wedged at ~99% and the `if: always()` upload preserved all four
process stacks. Raw dumps:
[evidence/run-27541609728/](evidence/run-27541609728/) (coverage job
`81404541787`, run `27541609728`). This is the first real frame — D1's
gate is now satisfied.

### What the stacks show

| Process | Main-thread frame | Reading |
|---------|-------------------|---------|
| controller | `xdist/dsession.py:154 loop_once → queue.get → threading wait` | waiting for a worker event that never arrives |
| gw1 | `execnet gateway_base serve → integrate_as_primary_thread → wait` | idle, done, awaiting shutdown |
| gw2 | same as gw1 | idle |
| gw3 | same as gw1 — **plus** a 3rd thread: `attune/memory/cross_session/coordinator.py:289 _heartbeat_loop → threading wait` | idle **+ a leaked heartbeat thread** |

### Classification — does NOT match H1/H2

Crucially, **no process is blocked in uninterruptible I/O** (no
`socket.recv`, no `subprocess.wait`, no `lock.acquire`). Every worker is
cleanly idle in execnet `serve`; the controller is cleanly idle in
`queue.get`. So this frame does **not** fit H1/H2 (the real-socket /
real-subprocess fixture-polluter family shared with
`windows-xdist-flakes`). It looks instead like an **execnet/xdist
end-of-session control-channel deadlock** (lost-wakeup at finalize):
all tests passed, but the session never concludes. Call it **H4**.

### The one differentiator — and why it's a LEAD, not a proven cause

The only thing distinguishing the wedged-fleet's `gw3` from gw1/gw2 is
a leaked `_heartbeat_loop` thread — a test called
`coordinator.start_heartbeat()` and never `stop_heartbeat()`, so the
thread persists for the worker's life. Candidates that start a
heartbeat: `tests/unit/memory/test_cross_session_coordinator.py`,
`tests/unit/workflows/test_execution_mixin_branches.py`,
`tests/unit/telemetry/test_agent_tracking.py`.

**But the causal chain is NOT closed.** The thread is `daemon=True`
(coordinator.py:271) and `_send_heartbeat` no-ops when there is no
Redis client (`client is None`) — which is exactly keyless CI. So in CI
it is a no-op daemon, and a no-op daemon thread should not deadlock
execnet. It is a strong **correlation / prime suspect**, not a
demonstrated cause. Do not ship a "fix" on one dump.

### Next actions (confirm-then-fix — tar-pit guarded)

1. **Gather 2–3 more captured frames** before committing to a fix.
   The key question: is the leaked-heartbeat thread present on the
   wedged worker **every** time, or was run-27541609728 a coincidence?
   The same PR's required `test (ubuntu-latest, 3.12)` lane PASSED
   while `coverage` wedged — confirming the hang is intermittent /
   worker-distribution-dependent, so N>1 dumps are needed to establish
   the pattern.
2. **Cheap defensive move (do regardless):** an autouse teardown
   fixture that stops any leaked coordinator heartbeat thread after
   each test. It removes the one variable that differs on the wedged
   worker, so the *next* dump is cleaner — and it is good hygiene
   even if H4 (execnet finalize race) turns out to be the real cause.
   Low-risk; its own scoped PR.
3. **If the leak is ruled out**, pivot to H4: investigate the
   execnet/xdist finalize handshake directly (the controller's
   `loop_once` waiting on `queue.get` while all workers idle in
   `serve` is the signature to research upstream).
4. **Verify with a rerun count** (≥10 clean `-n auto` reruns), never a
   single green — per the existing Phase 2 watch-out.

### Note for the sibling spec

`ci-gating-lane-isolation/requirements.md` described the hang as
freezing "~1s after start." This frame **disproves** that: the freeze
is a ~99% **finalize-wedge** (all tests pass, then the session can't
conclude). That spec's premise table is corrected in the same PR as
this finding. (This `ci-runner-hang` spec already had the "99%-freeze"
shape right.)

## Phase 3 — SECOND captured frame (2026-06-16, #924)

The N>1 dump the first frame called for. PR #924
(`chore(deps): adopt attune-rag 0.7.0`) wedged its
`test (ubuntu-latest, 3.11)` lane: every test passed, then the session
hung, the 14m step-timeout fired, the bounded auto-retry hung again, and
the job died with **exit code 124**. The `if: always()` upload preserved
all four stacks. Raw dumps:
[evidence/run-27615182285/](evidence/run-27615182285/) (job
`81649261853`, run `27615182285`).

### What the stacks show

| Process | Main-thread frame | Reading |
|---------|-------------------|---------|
| controller | `xdist/dsession.py:154 loop_once → queue.get → threading wait` | waiting for a worker event that never arrives |
| gw1 | `execnet gateway_base serve → integrate_as_primary_thread → wait` | idle, done, awaiting shutdown |
| gw2 | same as gw1 | idle |
| gw3 | same as gw1 | idle |

Identical **H4** controller signature to the first frame — clean idle
on every process, no uninterruptible I/O (no `socket.recv`,
`subprocess.wait`, or `lock.acquire`), so still **not** H1/H2.

### The discriminating result — heartbeat-leak lead WEAKENED

The first frame's only differentiator was a leaked
`coordinator.py _heartbeat_loop` thread on the wedged `gw3`, which
became the prime LEAD. **This frame reproduces the exact same
finalize-wedge with NO leaked heartbeat thread on any worker** (each
worker carries only its 2 execnet threads; `grep -ri heartbeat` over the
dumps is empty). Two consecutive H4 wedges, only one of which had the
leaked thread, argues the heartbeat thread was **incidental, not
causal** — the deadlock is in the execnet/xdist end-of-session control
channel itself.

This satisfies "Next actions" item 3 above (*if the leak is ruled out,
pivot to H4*): the cheap heartbeat-teardown fixture (item 2) is still
worth doing as hygiene, but the root-cause hunt should now target the
execnet/xdist finalize handshake directly, not the heartbeat leak.

## Phase 4 — heartbeat thread ruled out for the SEPARATE sys.modules flake (2026-06-22)

A different xdist symptom surfaced this session and could be mistaken
for this hang: `test_real_tools.py` flaked on one lane with
`KeyError: <object-id>` (fixed in #1003, guarded in #1004). It is
tempting to re-blame the leaked heartbeat thread as a "concurrent
`sys.modules` toucher" — **don't.** Evidence gathered while fixing it:

- `threading.enumerate()` in a clean keyless worker returns `[]` (no
  non-main threads) — verified in both xdist and single-process.
- The heartbeat loop **no-ops keyless** and is killed per-test by the
  autouse `_stop_leaked_heartbeat_threads` fixture, so it is not alive
  during an unrelated test's body.
- A concurrent importing thread does **not** reproduce the KeyError
  (20k `patch.dict("sys.modules")` teardowns, GIL-serialized, clean).
- Decisive: the failing key is an **int** (`id()`-shaped), but
  `sys.modules` keys are **strings** — so the KeyError is **not** from
  `sys.modules` at all. It is a re-entrant GC/finalizer touch of some
  `id()`-keyed cache triggered when `patch.dict`'s teardown runs
  `sys.modules.clear()`. Single-threaded re-entrancy, **no toucher to
  kill.**

Bottom line: killing the heartbeat thread would not have fixed the
sys.modules flake (the right fix was removing the `clear()`). The
heartbeat thread remains only a (weakened) suspect for the H4
finalize-wedge above, still gated on N>1 dumps — do not let the
sys.modules symptom revive it.

---

## Phase 2 update — 3rd capture, heartbeat exonerated, spawn fix + FD probe (2026-06-25)

A third hang was captured on the `coverage` lane of PR #1081 (run
`28188352287`, a trivial test-only PR). Dumps saved under
`evidence/run-28188352287/`.

### The signature is now confirmed and stable across 3 captures

All of `run-27541609728`, `run-27615182285`, and `run-28188352287`
show the identical end-of-session shape:

- **Controller:** wedged in `xdist/dsession.py loop_once -> queue.get()`
  (waiting on a worker event that never arrives); its N `_thread_receiver`
  threads all blocked in `execnet ... read`.
- **Workers:** every worker idle in `execnet ... serve()`
  (`integrate_as_primary_thread`) with **no test frame and no Pool
  frame** — i.e. they finished their assigned tests and returned to the
  execnet idle loop. Linux-only.

### The leaked heartbeat thread is exonerated as the cause

The `cross_session` heartbeat daemon thread (the prior "prime suspect")
appears in **only the oldest** capture (`run-27541609728`,
`coordinator.py:289 _heartbeat_loop`). The autouse
`_stop_leaked_heartbeat_threads` fixture shipped in **#914**
(2026-06-15); the two captures *after* it (06-16 and 06-25) contain
**no** heartbeat thread, yet the **identical** hang recurs. It is also
`daemon=True`, so it cannot block worker/process exit regardless.
Conclusion: not the cause. Do not revive it (see the sys.modules note
above for the prior near-miss).

### The signature matches a previously-fixed bug class (#930)

`tests.yml`'s coverage step documents the same shape, root-caused in
**#930**: *a fork-based `multiprocessing.Pool` inside an xdist worker
leaked the execnet socket fd, deadlocking the controller at ~99%;
Linux-only because macOS uses spawn.* An orphan fork/Pool child holding
a **dup** of a worker's execnet socket keeps the controller from ever
seeing EOF — and such a child is **invisible to faulthandler** (it
dumps only the controller + named workers), which is exactly why the
workers look idle with nothing pending.

#930's fix was a **threshold guard** (`_PARALLEL_MIN_FILES=50`) that
only *narrows* the window — it left
`scanner_parallel.py` building its Pool with the Linux-default **fork**.

### Actions taken this PR

1. **`scanner_parallel.py` -> `mp.get_context("spawn").Pool(...)`** —
   removes the fork-fd-inheritance hazard outright (macOS already does
   this). Verified a real 55-file parallel scan works under spawn.
   Regression test `test_large_scan_uses_a_spawn_pool` pins
   `get_context("spawn")`.
2. **Process-state probe** added to the conftest hang-watchdog: at the
   same threshold it writes `hang-dumps/hang-<worker>-proc.txt` with the
   global `ps` tree (cmdlines name a leaking child) and, on the
   controller, a socket-inode -> pid map (a worker's execnet inode held
   by an unexpected pid is the leaked fd). The captured hangs release
   the GIL (`queue.get` / socket `read`), so a Python timer fires.

### Caveat / why the probe still matters

The scanner Pool is **mocked in its unit tests** and `subprocess` calls
are `close_fds`-safe by default, so static analysis does **not** confirm
the scanner is the live trigger inside the coverage suite. The spawn fix
closes the one *known* fork hazard; the probe is what will **name the
actual orphan** on the next hang if a different fork/Pool path is
responsible. Tar-pit guard: if the next captured `*-proc.txt` shows no
leaked socket dup, the cause is genuinely xdist/execnet-internal and the
spec should go `monitoring` rather than chase further.

## Phase 2 close-out — 4th capture is WINDOWS; spec goes monitoring (2026-07-02)

A fourth hang was captured on PR #1212's `test (windows-latest, 3.12)`
lane (run `28566485306`). Dumps saved under
`evidence/run-28566485306/`. This capture changes the conclusion.

### The capture breaks two premises at once

- **"Linux-only" is falsified.** All three prior captures were Linux;
  this one is `windows-latest`. Same end-of-session shape: all tests
  passing, ~99% done, controller's execnet `_thread_receiver` threads
  blocked in `read`, worker in plain `threading.wait`, watchdog
  timeout at 20 min.
- **The fork-Pool fd-leak hypothesis cannot explain THIS hang.**
  Windows `multiprocessing` is spawn-only — `fork` does not exist on
  the platform — so a fork-dup'd execnet socket fd is impossible
  here. The one known fork hazard (already converted to spawn in
  #1085) is not the mechanism behind this capture.

### The #1085 probe was blind on Windows

`hang-controller-proc.txt` contains only `ps: unknown option -- w`
and an empty socket-inode map: the probe is built on `/proc` and
GNU `ps`, both Linux-only. So this capture cannot rule a leaked-fd
orphan in or out *on Windows* — but it doesn't need to: the platform
itself rules out fork.

### Conclusion: xdist/execnet-internal; spec -> `monitoring`

Per the tar-pit guard written into the 3rd-capture update ("if the
next capture shows no dup, the cause is genuinely
xdist/execnet-internal and the spec should go monitoring"): the 4th
capture, on a platform where the fork hypothesis is structurally
impossible, is the stronger version of that outcome. The
Phase-1 deliverables already bound the tax (job `timeout-minutes`
converts the wedge into a visible 20-min failure; `gh run rerun
--failed` recovered PR #1212 in one pass). Not building a
Windows-compatible probe (psutil/PowerShell) — that would be chasing
an unreproducible upstream bug past confirmed evidence. Reopen only
if a capture arrives with a test frame (not end-of-session) or an
upstream pytest-xdist/execnet fix becomes adoptable.

---

## Monitoring log — 5th capture: Windows again, segfault mid-dump (2026-07-06)

PR #1274's `test (windows-latest, 3.12)` lane (run `28772959348`)
wedged and died with **exit 139 (segfault)** after the 20-min
watchdog fired. Dumps saved under
[evidence/run-28772959348/](evidence/run-28772959348/). The spec
stays `monitoring` — this capture is logged as evidence, not a
reopen; nothing here revives a fixable hypothesis.

### Timeline (from the job log)

- Tests progressed normally to **94%** (last `[gw3] PASSED` at
  06:56:35Z), then output stopped — the familiar end-of-session
  freeze.
- Watchdog dump header `Timeout (0:20:00)!` fired; at 07:03:44Z the
  step died: `Segmentation fault  pytest -n auto --timeout=60
  --timeout-method=thread …` → exit 139, then the wrapper exited 1.
- The `if: always()` upload preserved the dumps (artifact
  `8101851811`).

### What the stacks show — and what's NEW

- **Controller:** four `_thread_receiver` threads all blocked in
  `execnet gateway_base.py:534 read` — the stable H4 signature,
  identical to captures 1–4.
- **NEW (a): the dump is truncated mid-write.** The controller's
  main-thread frame cuts off at `re/_parser.py:255 __next` — the
  segfault killed the process *while faulthandler was writing*. So
  unlike captures 1–4 the main thread was NOT idle in
  `dsession queue.get`; it was actively executing (regex parsing,
  plausibly an import/compile during teardown or plugin work). The
  frame below `re/_parser` is unrecoverable.
- **NEW (b): worker dumps are EMPTY** (`hang-gw2.txt`,
  `hang-gw3.txt`, 0 bytes) — the per-worker watchdogs never fired,
  i.e. no worker was wedged past threshold. Prior captures showed
  workers idle in `serve()`; this one can't say either way.
- **NEW (c): exit 139, not 124.** Prior Windows capture (#4, run
  `28566485306`) died by timeout kill; this one segfaulted. This is
  the second sighting of the exit-139/clean-log class first seen on
  the 10.0.1 release chain (#1272) — and the branch **contained**
  #1272's literal-loopback fix (`gh api compare` = `ahead`), so
  that fix does not cover this segfault path. The getaddrinfo
  hypothesis from #1272 is not confirmed here (no frame names it;
  the truncation hides the faulting call).

### Why this doesn't reopen the spec

Same tar-pit logic as the 4th-capture close-out: end-of-session
shape, no test frame, Windows (fork structurally impossible), and
the one new datum (segfault during faulthandler dump) points at
interpreter/teardown internals, not at our fixtures. The tax stayed
bounded: the lane is not in the required set, so PR #1274 merged
without it; `gh run rerun --failed` was kicked as hygiene.

**Monitoring tally: 5 captures** (3 Linux timeout-kill, 1 Windows
timeout-kill, 1 Windows segfault-mid-dump). Reopen criteria
unchanged, plus one addition: if a THIRD exit-139 arrives, consider
splitting "Windows teardown segfault" into its own tracked class —
two sightings in two days on the same lane suggests it may recur at
a higher rate than the wedge itself.
