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

If local:
- [ ] **3.1a** Rewrite the offending pattern (likely tighten fixture
      scope, replace MagicMock chains with explicit small mocks,
      or add cleanup)
- [ ] **3.2a** Restore the four files to CI (remove `--ignore`)
- [ ] **3.3a** Verify CI green

If structural:
- [ ] **3.1b** Extract redis-detection + short_term modules into a
      new `attune-redis` package (similar to attune-rag /
      attune-help / attune-author)
- [ ] **3.2b** Move tests with the package
- [ ] **3.3b** Add `attune-redis` to attune-ai's optional `[redis]`
      extra
- [ ] **3.4b** Update CI to test attune-redis separately
- [ ] **3.5b** Update docs/specs/larger-runners with the implication

## Out of scope

- Performance optimization of the redis pub/sub runtime (only the
  *test* memory matters here)
- General test-suite memory hygiene (Probe C is scoped to the
  cluster of 4 files)
- Larger-runners spec (separate, but related — see
  docs/specs/larger-runners/)
