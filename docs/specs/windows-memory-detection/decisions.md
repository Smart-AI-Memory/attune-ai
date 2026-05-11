# Decisions — Windows Memory-Feature Detection

**Status:** draft
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

## Working hypotheses (to verify, not commit to)

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
