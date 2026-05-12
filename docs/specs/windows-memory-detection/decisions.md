# Decisions — Windows Memory-Feature Detection

**Status:** approved
**Owner:** Patrick
**Opened:** 2026-05-11
**Predecessor:** `docs/specs/probe-c-memory-investigation/` (Phase 4 deferred — see PR #242)

---

## Problem

PR #242 (probe-c Phase 4 — restore `-n auto`) made Ubuntu + macOS lanes pass cleanly across Py 3.10–3.13 but **exposed 4 Windows-only test failures** that the prior `-n 1` cap had implicitly hidden: with serial execution + 12 platform lanes, Windows runs were consistently slow enough that some lanes hit the 75-min job timeout before completing. Parallelism (`-n auto`) made Windows finish in ~13 min, surfacing the failures for the first time.

**The 4 failures (Windows × all 4 Python versions, 2026-05-11):**

| Test | Failure mode |
|------|-------------|
| `tests/unit/test_memory_features.py::test_list_all_features_returns_dict` | xdist worker crashed |
| `tests/unit/test_memory_features.py::test_list_all_features_structure` | xdist worker crashed |
| `tests/unit/memory/test_redis_auto_detect.py::test_respects_redis_enabled_true` | xdist worker crashed |
| `tests/unit/hooks/test_session_continuity_io.py::test_above_threshold_fires_once` | TypeError: argument of type 'NoneType' is not iterable |

**Pattern:** 3 of 4 failures center on `MemoryFeatures.list_all_features()` / Redis auto-detection probing. The 4th is an unrelated subprocess wrapper issue.

These are not Probe C regressions — they have been latent since the affected code was written. They surface now because Phase 4 made Windows-on-time-budget viable.

---

## Decision

**Don't iterate ad-hoc in PR #242.** Per the tar-pit/spec-first rules:

1. Capture failures in this dedicated spec
2. Investigate each root cause separately
3. Fix in surgical PRs
4. Unblock #242 (the `-n auto` restoration) only after Windows is green again

PR #242 stays as draft until this spec's tasks 1–4 close. The `-n auto` win is real (3× faster CI, ~100+ compute-minutes saved per matrix run) and worth getting right.

---

## Phase 1 findings (2026-05-11, PR #245 run #25698758103)

The diagnostic workflow ran each of the 4 failing tests serially on `windows-latest` Py 3.11 with `--tb=long --capture=no`. Result was a **significant pivot** from the original hypotheses:

| Test | Outcome | Implication |
|------|---------|-------------|
| `test_list_all_features_returns_dict` | ✅ **PASSED** in isolation | Not a Windows-portability bug; fails only under parallel execution |
| `test_list_all_features_structure` | ✅ **PASSED** in isolation | Same |
| `test_respects_redis_enabled_true` | ✅ **PASSED** in isolation | Same |
| `test_above_threshold_fires_once` | ❌ **FAILED** in isolation | Genuine Windows bug |

**Pivot:** Hypothesis A (Linux-only probing in `MemoryFeatures.list_all_features()`) is **disproven**. The 3 memory tests are Windows-clean when run serially. The xdist worker crashes under `-n auto` are caused by xdist process management on Windows (which uses `spawn`, not `fork`, and is heavier and more fragile than POSIX) or by state pollution from a concurrent test in a different worker.

Hypothesis B (hook subprocess wrapper) is **partially confirmed** but more puzzling than expected. The diagnostic showed `first.stdout is None` at the failing assertion despite `_run_hook` using `capture_output=True, text=True` — per Python docs, that combination should always produce a string. A deeper diagnostic step is queued (commit `ea92b9a0`) that calls `subprocess.run` directly and prints `repr(result.stdout)` so we can see what's actually happening on Windows.

## Revised plan

### For the 3 memory tests
The fix is NOT in the tests or in `MemoryFeatures.list_all_features()`. Options:

1. **`@pytest.mark.no_xdist`** on the 3 tests — force serial execution for them. Trades a few seconds of parallelism for stability.
2. **`pytest-forked`** — give the 3 tests their own subprocess. Heavier but clean isolation.
3. **`--dist=loadgroup`** with `xdist_group` markers — group these tests on one worker. Less granular but cheaper than forked.
4. **Stop the bleeding from upstream** — find what test is leaving cross-worker state on Windows and fix it.

(4) is the principled fix but high-effort. (1) is the pragmatic fix. Decide after seeing if a 5th test surfaces during Phase 4 rebase.

### For the hook test
Continue debugging in Phase 1's second diagnostic step. Most likely candidates after seeing `repr(stdout)` result:

- Empty string (`""`) — hook returned early without writing. Theory: `estimate_utilization` raises on Windows and the `except` block routes to stderr.
- `None` — would indicate `subprocess.run`'s behavior diverges from docs on Windows.
- Some Windows-specific bytes — encoding issue at the subprocess pipe.

---

## Working hypotheses (superseded by Phase 1 findings above — kept for history)

### Hypothesis A — `MemoryFeatures.list_all_features()` uses Linux-only probing

The 3 worker crashes are clustered in code paths that touch `MemoryFeatures.list_all_features()` (directly or via `is_redis_enabled` probe). Likely culprits inside that call:

- `socket.AF_UNIX` socket-existence check for local Redis — doesn't exist on Windows, can raise `AttributeError` or `OSError(EAFNOSUPPORT)`
- `psutil`/`os.uname()` calls — `os.uname()` is Unix-only
- File path probes using `/var/run/...` or `/tmp/redis.sock`-style paths
- `subprocess.run(["redis-cli", ...])` without `shell=True` — Windows might fail differently
- Reading `/etc/redis/redis.conf` style paths

A worker "crash" (not test failure) means the worker process died, suggesting an unhandled C-level exception (OSError without catch, segfault from a native dep). Need to capture the actual exception text — xdist truncates it to "worker crashed".

### Hypothesis B — `_run_hook()` subprocess wrapper has a Windows encoding gap

`test_above_threshold_fires_once` uses `_run_hook()` which spawns the hook script via subprocess. `TypeError: argument of type 'NoneType' is not iterable` on the assertion `"context at 100%" in first.stdout` suggests `first.stdout` is `None`, which means the subprocess returned no captured output. Possible causes:

- `_run_hook()` doesn't pass `capture_output=True` consistently — Linux defaults differ from Windows
- Hook script shebang doesn't resolve on Windows (`#!/usr/bin/env python` — Windows lacks `env`)
- Hook script writes to stderr but the test only checks stdout
- Process exits without flushing stdout (timing issue)

Smallest reproduction would be to run `_run_hook(_COMPACT_WARNING, ...)` on a Windows runner and print `result.stdout`, `result.stderr`, `result.returncode` BEFORE the assertion.

---

## Out of scope

- Restoring Windows xdist parallelism beyond the existing `-n auto` — if Windows worker crashes prove un-fixable for these specific tests, falling back to `@pytest.mark.skipif(sys.platform == "win32", reason="...")` per-test is acceptable. Goal is "Windows CI is green and meaningful", not "every test runs on every platform".
- Fixing latent Windows fragility in unrelated subsystems (workflows, agents). Stay focused on memory-detection + the one hook test.
- Re-evaluating `-n auto` itself. PR #242 is parked on this work, not invalidated by it.

---

## Resolution criteria

Spec closes when:

1. Each of the 4 failures has a root-cause line item in `decisions.md` (one paragraph per test)
2. Either: fix lands, OR the test is documented-and-skipif'd with an issue link
3. PR #242 rebases on the new main and **all 12 platform lanes pass** under `-n auto`
4. CI total wall time on the matrix < 10 min average (verifies the `-n auto` payoff)

---

## 2026-05-12 — Phase 2 + Phase 3.1 attempt (worktree `interesting-mclaren-7de1e4`)

Findings from a fresh re-diagnosis (without re-running the diagnostic
workflow):

### Memory-feature cluster — root cause identified

The Phase 1 pivot's framing ("Windows xdist process management" /
"cross-worker state pollution") was directionally right but missed
the proximate cause. `MemoryFeatures.list_all_features()` called
`is_redis_running()` **five times per invocation** — once per Redis
feature in `get_feature_status()`. Each call opens a real socket to
`localhost:6379` with a 1s connect timeout. On Windows under
xdist `-n auto` with 12 workers concurrently probing the same closed
port, the cumulative socket pressure crashed workers. Confirmed
by inspection of `src/attune/memory/features.py:138-159` against
`list_all_features()` at the same file.

### Fix (this worktree)

In `MemoryFeatures.list_all_features()`: probe `is_redis_available()`
and `is_redis_running()` **once** at the top and reuse the result for
all 5 Redis features. Behavior is unchanged (the result wouldn't
differ across the 5 calls within a single invocation). Local timing
drops from ~5s worst-case to ~0.04s. Phase 1's hypothesis B
("Windows xdist process management") is the *symptom*; this
deduplication is the proximate fix.

Regression test added: `test_list_all_features_probes_redis_once`
asserts `is_redis_available` and `is_redis_running` are each called
exactly once per `list_all_features()` invocation. Catches regressions
that would re-introduce per-feature probing.

### Hook test (Phase 3.1) — also fixed

`test_above_threshold_fires_once` and the two other open-coded
`subprocess.run` calls in `tests/unit/hooks/test_session_continuity_io.py`
used `text=True` without an explicit encoding. The hook emits
`⚠️` (U+26A0) which forces non-ASCII bytes onto stdout. Windows
default locale (cp1252) decoding is the most likely culprit. Fix:
swap `text=True` for `encoding="utf-8", errors="replace"` on all
three subprocess calls. Matches the existing CLAUDE.md lesson on
Windows encoding for `Path.read_text` and the hook's own
`reconfigure(encoding="utf-8", errors="replace")` on `sys.stdout`.

### test_respects_redis_enabled_true — also fixed (test-only)

This is the 3rd "memory cluster" failure but has a different root
cause from the other two. `BaseOperations.__init__` calls
`_create_client_with_retry`, which blocks for up to 17 seconds
(3 retries × 5s socket connect timeout) when no Redis server is
running. The test relied on `try/except Exception: pass` to swallow
the resulting failure, but under xdist on Windows the 17s blocking
I/O × 12 workers crashed worker processes.

Fix: patch `BaseOperations._create_client_with_retry` to return
`None` for the duration of the test. The assertion that matters
(`auto_detect_redis.assert_not_called()`) is preserved — the actual
client connection was incidental to the test's purpose. Production
code unchanged.

### Next verification step

Push these changes and confirm 12/12 matrix green under `-n auto`.
All 4 documented Windows failures should now be addressed.
