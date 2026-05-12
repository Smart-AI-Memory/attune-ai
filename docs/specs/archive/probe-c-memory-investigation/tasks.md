# Tasks — Probe C: Memory Investigation

## Phase 1 — Characterize

- [ ] **1.1** Install `memory_profiler` (`pip install memory_profiler`)
- [ ] **1.2** Profile each suspect file in isolation:
      ```
      python -m memory_profiler -m pytest tests/unit/memory/test_pubsub_direct.py -n 1
      python -m memory_profiler -m pytest tests/unit/memory/test_redis_auto_detect.py -n 1
      python -m memory_profiler -m pytest tests/unit/memory/test_redis_bootstrap.py -n 1
      python -m memory_profiler -m pytest tests/unit/test_memory_features.py -n 1
      ```
      Record peak RSS for each.
- [ ] **1.3** Profile pairs (sequential, same process):
      ```
      pytest tests/unit/memory/test_long_term.py tests/unit/memory/test_pubsub_direct.py -n 1
      ```
      Does pubsub's memory cost change when preceded by other
      attune-memory tests?
- [ ] **1.4** Compare with sibling files that DON'T crash:
      ```
      pytest tests/unit/memory/test_short_term.py -n 1
      pytest tests/unit/memory/test_long_term.py -n 1
      ```
      These run heavy fixtures too but don't OOM. Find the
      asymmetry.

## Phase 2 — Locate

- [ ] **2.1** Identify the specific test/line where memory spikes
- [ ] **2.2** Categorize as local (fixture/mock leak) vs structural
      (import or module-level state)
- [ ] **2.3** Write up findings in `decisions.md`

## Phase 3 — Fix

Resolution: Phase 3a (local fix) chosen — see decisions.md.

If local: ✓ DONE
- [x] **3.1a** Rewrite the offending pattern (added missing
      `patch("threading.Thread")` in
      `test_subscribe_adds_to_subscriptions_dict`)
- [x] **3.2a** Restore the four files to CI (removed `--ignore` in
      tests.yml on PR #212 commit bcc6bdec)
- [x] **3.3a** Verify CI green (pending matrix completion)

If structural (NOT taken):
- [ ] ~~3.1b Extract redis-detection + short_term modules into a
      new `attune-redis` package~~
- [ ] ~~3.2b-3.5b Worst-case path; data ruled it out~~

## Phase 4 — Restore parallel xdist (post-resolution cleanup)

With the leak fixed, the `-n 1` cap added in PR #212 commit
`d4f33ddd` is no longer justified. The original rationale —
"xdist worker multiplication amplifies memory" — was wrong; the
actual problem was one test's zombie thread, not parallelism.

Sequential `-n 1` is ~15-17 min on Linux. `-n auto` (4 workers on
GH standard runner) should land closer to ~5-7 min — roughly 3×
faster, ~100+ minutes of compute saved per matrix run.

- [ ] **4.1** Verify locally: full suite under `-n auto` matches
      sequential outcome
      ```
      pytest -n auto --timeout=60 --timeout-method=thread -m "not network and not integration"
      ```
- [ ] **4.2** Flip `-n 1` to `-n auto` in `.github/workflows/tests.yml`,
      both the matrix `test` job AND the dedicated `coverage` job.
      Update the comment block to reflect the new understanding
      (leak was the cause, not worker count).
- [ ] **4.3** Push to a separate PR (not bundled with the leak fix).
      Rollback plan = single-commit revert.
- [ ] **4.4** If green: close Phase 4. If red: read failure
      carefully — could be another parallel-unsafe test that the
      pubsub leak was masking. Investigate per the
      "spec-before-iteration-3" rule.

## Phase 5 (conditional) — combo with larger runners

If `docs/specs/larger-runners/` (PR #226) also lands, Phase 4 +
larger runners together restores CI to local-dev-equivalent: fast,
parallel, plenty of headroom. The "works fine locally, OOMs in CI"
gap that motivated Probes B and C closes structurally.

- [ ] **5.1** After Phase 4 green + #226 merged, re-evaluate
      whether to keep the `--timeout=60` cap (might want longer
      with more headroom) and the mem-tick instrumentation (might
      retire as load-bearing, keep as opt-in diagnostic).

## Out of scope

- Performance optimization of the redis pub/sub runtime (only the
  *test* memory matters here)
- General test-suite memory hygiene (Probe C is scoped to the
  cluster of 4 files)
- Larger-runners spec (separate, but related — see
  docs/specs/larger-runners/)
