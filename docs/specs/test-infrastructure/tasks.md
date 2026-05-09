# Spec: Test Infrastructure Reliability

**Status**: draft

---

## Phase 3: Tasks

### Phase 2A — Diagnose

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Reproduce historical xdist failure: temporarily flip `pytest.ini` `-n 0` → `-n auto`, run full suite, capture failure mode (import error / race / passes). | test-infra | todo | Output: written diagnosis with file:line citations of the failure point. |
| 2 | Inspect `src/attune/workflows/__init__.py` and direct dependencies for module-level side effects: singleton construction, circular-import workarounds, auto-discovery, etc. | src/attune/workflows | todo | Output: side-effects-at-import diagram. |
| 3 | Memory-profile a single-process run with `tracemalloc`. Identify dominant allocation sites and whether they're plugin overhead, fixture leaks, module-level state, or unavoidable test cost. | test-infra | todo | Output: top-10 allocation report + fixability recommendation. |
| 4 | Audit the three `--ignore`-d test files (`test_execution_and_fallback_architecture.py`, `test_composition_patterns.py`, `test_orchestrated_release_prep.py`) for whether they're salvageable or should be deleted. | tests | todo | One of: fix-and-restore, delete-with-justification, or convert-to-skip-with-reason. |
| 5 | Profile `tests/unit/memory/test_pubsub_direct.py` to identify why it takes 44s for 40 tests. Likely candidates: real Redis connections, asyncio sleep waits, fixture teardown. | test-infra | todo | Output: per-test timing + recommendation. |

### Phase 2B — Decide

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 6 | Pick path A / B / C from design.md based on Phase 2A findings. Document rationale in this file. | spec | todo | Blocked by 1-3. |

### Phase 2C — Implement (path-dependent)

#### If Path A or C (re-enable xdist)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7A | Fix the workflows-package import-timing issue identified in #2. | src/attune/workflows | todo | Specifics depend on findings. May require moving module-level initialization into lazy properties or fixture-style setup. |
| 8A | Set `pytest.ini` `addopts` to `-n auto` (or `-n logical`). Remove the legacy `-n 0` and the explanatory comment. | pytest.ini | todo | Validate full suite passes locally on dev hardware. |
| 9A | Audit shared-state hazards exposed by parallel execution. Common culprits: tmp_path collisions (use `tmp_path_factory`), sqlite/redis fixtures with non-unique names, module-level caches. | tests | todo | Each finding becomes a sub-task to fix. |

#### If Path B or C (fix memory growth)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7B | Address dominant allocation sites identified in #3. Examples: replace session-scope fixtures with function-scope, drop pytest plugins that retain global state, fix module-level caches that aren't cleared between tests. | tests | todo | Specifics depend on profile findings. |
| 8B | Validate full suite runs to completion on a 16GB dev machine without OOM. | test-infra | todo | Acceptance criterion from requirements.md G1. |

### Phase 2C — Implement (cross-path)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | Resolve the three `--ignore`-d files per #4's findings. | tests | todo | Either delete the ignore directives + tests pass, or delete the files + remove imports + remove ignore lines. |
| 11 | Resolve `pubsub_direct.py` slowness per #5's findings. | tests / src/attune/memory | todo | Either accept (with documented reason) or fix. |
| 12 | Retire `scripts/clean_test_artifacts.sh` and `scripts/run_tests_chunked.sh` once #8 (A or B) lands. Update `CONTRIBUTING.md` to remove their sections. | scripts / docs | todo | Workarounds are explicitly named as such in their docstrings; deletion is the success signal. |
| 13 | Update `docs/COVERAGE_BUG_LOG.md` with this spec's outcome. The "infrastructure debt" caveat in the project-health summary should be removable. | docs | todo | Cosmetic but signals completion to anyone reading the bug log. |

### Validation

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 14 | New-dev smoke: clone the repo into a fresh directory, run `pytest tests/`. Must complete green within 10 minutes on a 16GB machine. | manual | todo | Requirements.md acceptance criterion. |
| 15 | CI parity check: confirm CI is still green after the changes; no test that passed before passes-or-fails differently after. | CI | todo | Any drift means a latent shared-state issue surfaced by the parallel switch. |

### Failure-to-deliver path

If #1–3 reveal that the underlying fix is prohibitively expensive,
mark this spec as **deferred**, document findings in
`docs/specs/test-infrastructure/findings.md`, add a Makefile target
that wraps `scripts/run_tests_chunked.sh` as `make test`, and
explicitly preserve the workarounds as the supported path in
`CONTRIBUTING.md`. Open a follow-up issue for a future attempt.
