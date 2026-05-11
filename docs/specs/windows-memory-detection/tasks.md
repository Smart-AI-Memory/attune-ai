# Tasks — Windows Memory-Feature Detection

**Status:** approved

Investigation + fix tasks for the 4 Windows-only failures surfaced by PR #242 (`-n auto` restore). See `decisions.md` for context.

---

## Phase 1 — Characterize (no fixes yet)

Goal: turn "worker crashed" into a concrete exception trace so we know what to fix.

- [ ] **1.1** On a Windows runner (CI matrix `test (windows-latest, 3.11)` is sufficient), run the 3 memory-feature tests serially with full traceback:
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

The 3 worker crashes likely share a root cause (Linux-only probe in `MemoryFeatures.list_all_features()` or its `is_redis_enabled()` helper). One fix may close 3 tests.

- [ ] **2.1** Locate the offending probe (`grep -rn "AF_UNIX\|os.uname\|/var/run\|/tmp/redis" src/attune/memory/`).
- [ ] **2.2** Add platform-aware guards:
      ```python
      if sys.platform == "win32":
          # skip the Unix-only probe; return a default or use the
          # Windows-appropriate alternative
      ```
      Where the probe IS the feature (e.g. AF_UNIX socket detection), the Windows path is "always-unavailable, return `FeatureStatus.MISSING_DEPENDENCY` with an install hint".
- [ ] **2.3** Add a regression test that exercises the new branch with `sys.platform` patched, so we don't lose coverage on Linux.
- [ ] **2.4** Verify with the Phase 1 diagnostic command — the 3 tests should pass on Windows.

## Phase 3 — Fix the hook subprocess wrapper

- [ ] **3.1** Once Phase 1.3 tells us what's `None`, write a targeted fix. Likely one of:
      - Add `text=True, encoding="utf-8"` to `subprocess.run` calls in `_run_hook()`
      - Switch the hook script invocation to `[sys.executable, str(script_path), ...]` instead of relying on shebang resolution
      - Pass `shell=False` explicitly (Windows default differs)
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
