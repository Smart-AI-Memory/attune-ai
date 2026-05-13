# Spec: Test Infrastructure Reliability
**Status:** approved
---

## Phase 1: Requirements

### Problem statement

The local test execution story is broken in ways that compound:

1. **`pytest tests/` OOMs on most dev machines.** `pytest.ini` forces `-n 0`
   (sequential) because of "import timing issues with workflows package," so
   the single pytest process accumulates memory across the ~5000-test suite
   and OOMs on standard hardware. CI sidesteps the issue by running each
   matrix job (3 OS × 4 Python versions) on a fresh VM.

2. **No single "is everything green?" command works locally.** The chunked
   runner (`scripts/run_tests_chunked.sh`, added in commit `91678bc1`)
   exists as a workaround, not a fix. It confirms each chunk passes
   independently but doesn't catch interaction bugs that only manifest in
   a single-process run.

3. **Coverage data shards corrupt across runs.** `.coverage.<host>.<pid>.<rand>`
   files left from prior parallel-coverage runs cause new runs to fail with
   `"Data file ... doesn't seem to be a coverage data file"`.
   `scripts/clean_test_artifacts.sh` (commit `50daeec7`) clears them but
   has to be invoked manually.

4. **Stale pytest processes accumulate.** During a single coverage push
   session, three orphaned pytest processes consumed ~14 GB of RAM. Either
   pytest doesn't always clean up after timeouts, or the dev workflow
   doesn't have a kill-stragglers habit.

5. **Three test files are `--ignore`-d in `pytest.ini`** because they fail
   for reasons that haven't been resolved: `test_execution_and_fallback_architecture.py`,
   `test_composition_patterns.py`, `test_orchestrated_release_prep.py`.
   Each ignore is a piece of test debt accumulating over time.

6. **`pubsub_direct.py` is anomalously slow** (44s for 40 tests). Suggests
   heavy fixture setup or genuine slow operations. Bundling it with other
   files contributes to the OOM.

The compounding effect: developers can't run the full suite locally, so
they don't, so failures only surface in CI, so iteration is slow, so the
infrastructure problems don't get fixed because nobody hits them in the
fast feedback loop where fixes are cheap. **Test infrastructure is the
single biggest leverage point for overall project velocity.**

### Goals

- **G1: A single command runs the full suite locally and produces a
  pass/fail signal.** No chunking workaround, no manual cleanup between
  runs.
- **G2: Local and CI test signals are equivalent.** What passes/fails
  in CI passes/fails locally on a developer machine of comparable specs.
- **G3: The three currently-`--ignore`-d test files are either fixed or
  formally retired with documented justification.**
- **G4: `pubsub_direct.py`'s slowness has a documented cause** —
  either accepted as inherent (e.g. real timing-dependent behavior) or
  fixed.

### Non-goals

- **Not redoing CI.** GitHub Actions matrix is fine; this spec is about
  local parity, not CI architecture.
- **Not converting the test suite to a different framework.** pytest stays.
- **Not reducing the test count.** The goal is to make the existing tests
  runnable, not to delete them.

### Success criteria

- `pytest tests/` exits cleanly on a 16GB RAM dev machine within 10 minutes.
- The `--ignore` directives in `pytest.ini` for the three known-failing
  files are either removed (because the tests were fixed) or replaced
  with `pytest.skip` / deletion + documented reason.
- A new dev cloning the repo and running `pytest tests/` once gets a
  green result — no manual steps, no chunking, no cleanup invocations.
- `scripts/clean_test_artifacts.sh` and `scripts/run_tests_chunked.sh`
  can be deleted when this spec is complete (they're explicitly named
  workarounds in their docstrings).

### Risks

- **Re-enabling xdist may surface latent test interdependencies.** Tests
  that pass sequentially because of shared state (module-level globals,
  file-system fixtures, etc.) may fail under parallel execution. This
  is itself a quality finding, but it expands scope.
- **The "import timing issues with workflows package" comment is the
  only documentation of why `-n 0` was set.** The original issue may
  not be reproducible if the underlying code has changed since the
  decision was made — diagnosis Phase 2 may end up "issue no longer
  applies, just enable xdist." Or it may be a real concurrency hazard
  that requires structural changes to `src/attune/workflows/__init__.py`.
- **Fixing the slow `pubsub_direct.py` may require Redis or asyncio
  changes** rather than test-only fixes, expanding scope.
