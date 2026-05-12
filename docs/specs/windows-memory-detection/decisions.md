# Decisions — Windows Memory-Feature Detection

**Status:** complete (2026-05-12)
**Owner:** Patrick
**Opened:** 2026-05-11
**Closed:** 2026-05-12 (PR #242 merged `5e364653`)
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

---

## 2026-05-12 (later) — PR #242 surfaces 2 new failures on rebase

After PRs #260 and #261 merged, PR #242 was rebased onto the new
main (commits `5f55a451` and `f05727fe`, force-pushed) and marked
ready. The post-rebase CI run revealed a NEW failure pattern that
the original 4 didn't cover:

| Test | Lanes failing | Lanes passing |
|------|--------------|---------------|
| `tests/unit/memory/short_term/test_conflicts.py::TestCreateConflictContext::test_logs_creation_event` | Ubuntu × 4, Windows × 3 (3.11–3.13) | macOS × 4, Windows 3.10 |
| `tests/unit/memory/short_term/test_conflicts.py::TestResolveConflict::test_logs_resolution_event` | Same as above | Same |

Both assert structlog output via `capsys` (`assert "conflict_..."
in captured` where `captured == ""`). The capsys version was on
PR #242's branch — added originally by PR #263 (`4d8f387c`) earlier
the same day. They pass under `-n 1` (the configuration PR #263
shipped under) but fail under `-n auto` (what PR #242 restores)
because structlog routing in xdist workers doesn't reach the
worker's `capsys` stream.

**Important correction**: main's current version of
`test_conflicts.py` already uses the xdist-safe pattern
(`structlog.testing.capture_logs()` with `reset_defaults()`).
That fix landed via PR #265 (`21e7cefc`, merged 12:28 EDT today)
AFTER PR #242's rebase ran (14:30 UTC). So PR #242's branch had
the pre-#265 capsys version, and the rebase missed the fix
because the rebase base predated it.

This is the "5th test surfaces during rebase" scenario Phase 4.3
of `tasks.md` anticipated, with a wrinkle: the fix already exists
upstream; PR #242 just needs to pick it up.

### Resolution

The minimal fix is to restore main's version of `test_conflicts.py`
on PR #242's branch (`git checkout origin/main --
tests/unit/memory/short_term/test_conflicts.py`). Committed and
pushed as `7eef6abc` on `feat/probe-c-phase4-restore-n-auto`. CI
should now re-run with the xdist-safe version.

Alternative (cleaner but more work): re-rebase PR #242 onto current
main, which would naturally pick up #265's fix. Skipped because the
surgical file-restore is equivalent and avoids another force-push.

Recommend option 1 in the next session focused on PR #242. Spec
remains open with one outstanding criterion (resolution-criteria
item 3: all 12 platform lanes green under `-n auto`).

### Lesson captured

Restoring `-n auto` after a branch lag surfaces tests landed on
main under `-n 1` that aren't xdist-safe. Generalization captured
in CLAUDE.md.

---

## 2026-05-12 (final) — Spec closed

PR #242 merged at `5e364653`. CI re-ran the full 12-lane matrix
with the `test_conflicts.py` fix and all 12 lanes passed.

**Resolution criteria — all satisfied:**

1. ✅ Each of the 4 original failures has a root-cause line item
   in this file (Phase 2 + 3.1 entries above).
2. ✅ Fixes landed for all 4 — no skipif fallbacks needed.
3. ✅ PR #242 rebased on the new main and **all 12 platform lanes
   passed** under `-n auto`.
4. ✅ Matrix wall time well under 10 min on the post-fix run.

**PRs merged today (2026-05-12) closing this spec:**

| PR | Title | Merge commit |
|----|-------|--------------|
| #260 | fix(ci): resolve 4 Windows-only test failures | `46492dc0` |
| #261 | docs(lessons): three CI-debugging lessons | `9a82cbbc` |
| #242 | ci(tests): restore `-n auto` — probe-c Phase 4 | `5e364653` |

The `-n auto` win is now realized: ~3× faster CI matrix on Windows,
~100+ compute-minutes saved per matrix run. All four Windows tests
green, plus the late-surfacing `test_conflicts.py` capsys regression
caught and fixed during PR #242's CI verification.

Spec status: **complete**. Predecessor
`probe-c-memory-investigation` Phase 4 also closes.
