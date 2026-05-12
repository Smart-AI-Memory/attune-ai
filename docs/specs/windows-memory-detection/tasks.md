# Tasks — Windows Memory-Feature Detection

**Status:** approved

Investigation + fix tasks for the 4 Windows-only failures surfaced by PR #242 (`-n auto` restore). See `decisions.md` for context.

---

## Phase 1 — Characterize (no fixes yet)

**Status (2026-05-11):** First diagnostic run complete via PR #245 — see `decisions.md` "Phase 1 findings". Major pivot: 3 of 4 tests PASSED in isolation on Windows, so they're parallel-context bugs (xdist on Windows), not Windows-portability bugs. Second diagnostic step (deep subprocess inspection for the hook test) is queued.

Goal: turn "worker crashed" into a concrete exception trace so we know what to fix.

- [x] **1.1** On a Windows runner (CI matrix `test (windows-latest, 3.11)` is sufficient), run the 3 memory-feature tests serially with full traceback:
      ```
      pytest tests/unit/test_memory_features.py::TestMemoryFeatures::test_list_all_features_returns_dict \
             tests/unit/test_memory_features.py::TestMemoryFeatures::test_list_all_features_structure \
             tests/unit/memory/test_redis_auto_detect.py::TestBaseOperationsBackwardCompat::test_respects_redis_enabled_true \
             -n 1 --tb=long -v --capture=no
      ```
      Tactic: push to a throwaway branch with this command in `.github/workflows/tests.yml` instead of the normal pytest call (revert before merge — purely diagnostic). The point is to get the real traceback that xdist would otherwise eat.

- [ ] **1.2** Read the traceback for each failure and add a one-paragraph root-cause note to `decisions.md`'s "Working hypotheses" section, promoting them from hypothesis to fact.

- [ ] **1.3** For the hook subprocess failure (`test_above_threshold_fires_once`):
      ```
      pytest tests/unit/hooks/test_session_continuity_io.py::TestCompactWarning::test_above_threshold_fires_once \
             -n 1 --tb=long -v --capture=no
      ```
      Look for: is `subprocess.run` returning `None` for `stdout`? Is the hook script's shebang resolving? Capture `result.stderr` if `result.stdout is None`.

## Phase 2 — Fix the memory-feature cluster

**Status (2026-05-12):** Hypothesis revised — actual root cause is
network probe contention, not a Unix-only API. See `decisions.md`
"2026-05-12 — Phase 2 + Phase 3.1 attempt".

- [x] **2.1** Locate the offending probe — `grep` returned NO hits
      for `AF_UNIX|os.uname|/var/run|/tmp/redis` in `src/attune/memory/`.
      Real root cause: `list_all_features()` called `is_redis_running()`
      5× per invocation, each a real socket probe to localhost:6379
      with 1s timeout. Under xdist on Windows the cumulative socket
      pressure crashed workers.
- [x] **2.2** Fix: dedupe the probe in `list_all_features()` to once
      per call. Behavior unchanged (result wouldn't differ across the
      5 calls within one invocation). No platform-aware guard needed.
- [x] **2.3** Regression test added:
      `test_list_all_features_probes_redis_once` in
      `tests/unit/test_memory_features.py` asserts `is_redis_available`
      and `is_redis_running` each called exactly once per
      `list_all_features()` invocation.
- [x] **2.4 (extended)** Also fixed `test_respects_redis_enabled_true`
      via a test-only change. Root cause was different from the other
      two: `BaseOperations.__init__` calls `_create_client_with_retry`
      which blocks for up to 17s (3 retries × 5s socket timeout) when
      no Redis server is running. The test relied on `try/except` to
      swallow the failure, but under xdist on Windows the 17s blocking
      I/O × 12 workers crashed worker processes. Fix: patch
      `_create_client_with_retry` to return `None`. The test still
      verifies `auto_detect_redis.assert_not_called()` — the actual
      client connection was incidental to the test's purpose.
- [ ] **2.5** Verify all 3 memory-cluster tests pass on Windows
      under `-n auto`. (Push pending.)

## Phase 3 — Fix the hook subprocess wrapper

- [x] **3.1** Fix applied: replaced `text=True` with
      `encoding="utf-8", errors="replace"` on all three `subprocess.run`
      calls in `tests/unit/hooks/test_session_continuity_io.py`
      (the `_run_hook` helper plus two open-coded calls). The hook
      emits `⚠️` (U+26A0); Windows default cp1252 decoding is the most
      likely culprit. Matches the existing CLAUDE.md lesson on Windows
      encoding for `Path.read_text`. Verification on Windows CI pending.
- [ ] **3.2** Add a guard test that asserts `result.stdout is not None` after `_run_hook()` returns, regardless of platform. Fast fail if the wrapper breaks again.

## Phase 4 — Unblock PR #242

- [ ] **4.1** Rebase `feat/probe-c-phase4-restore-n-auto` onto main (which now has Phase 2 + 3 fixes).
- [ ] **4.2** Mark PR #242 ready for review (un-draft via `gh pr ready 242`).
- [ ] **4.3** Verify all 12 platform lanes green under `-n auto`. If a fifth Windows test surfaces, append it to this spec's `decisions.md` and don't merge — return to Phase 1 with the new test.
- [ ] **4.4** Admin-merge #242.
- [ ] **4.5** Close `docs/specs/probe-c-memory-investigation/` Phase 4 (mark 4.4 ✅, no Phase 5 unless `docs/specs/larger-runners/` activity resumes).

## Phase 5 (conditional) — Punt on stubborn Windows tests

If Phase 2 or 3 fixes can't be made within ~2 hours of focused work, fall back:

- [ ] **5.1** Add `@pytest.mark.skipif(sys.platform == "win32", reason="<spec link>")` to the affected test(s).
- [ ] **5.2** Open a GitHub issue per skipped test with the exception trace from Phase 1, link to this spec.
- [ ] **5.3** Note the skips in `decisions.md` "Out of scope" — they are debt, not closure.

The bar for Phase 5 is high: only invoke after a real Phase-2/3 attempt fails. Skipping tests as a first move turns Windows CI into a meaningless rubber-stamp.

---

## Out of scope (parking lot)

- Other Windows-fragile tests not in the 4-test list. Add to this spec only if they surface during Phase 4.3 (rebase) — otherwise file separately.
- General Windows performance work. The `-n auto` payoff is enough.
