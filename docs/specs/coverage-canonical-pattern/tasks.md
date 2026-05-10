# Tasks: Canonical Coverage Pattern

**Status**: draft

---

## Phase 3: Tasks

### Phase 0 — Hypothesis verification (cheap probes before architectural change)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 0a | **Probe A**: drop `--cov-report=term-missing` from `.github/workflows/tests.yml` test step. Push to PR #212, watch matrix. **Decision point**: if matrix passes (≥10/12 green), close this spec — Phase 1+ unnecessary. If matrix still fails with the same `[100%] PASSED → shutdown` pattern, output-buffer pressure ruled out, proceed to 0b. | .github/workflows/tests.yml | todo | Single-line change. Lowest possible cost. Tests one specific theory. |
| 0b | **Probe B**: add memory monitoring to the test step — pre-test `free -m`, parallel monitor logging every 30s, post-test `free -m`. Captures whether memory actually spikes during the suspected merge step. **Decision point**: if memory near limit at shutdown → OOM confirmed, proceed to Phase 3A. If memory has headroom → hypothesis wrong, pause spec and investigate alternative causes (network, log-buffer, GH Actions internal). | .github/workflows/tests.yml | todo | Only execute if 0a fails. ~10 YAML lines. |

**Gate**: only proceed to Phase 3A if Probe A fails AND Probe B confirms memory exhaustion.

### Phase 3A — Local groundwork (no push until all 3A tasks pass)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Add project-root `sitecustomize.py` calling `coverage.process_startup()`. | src | todo | Per design.md "Bootstrap file" Option A. |
| 2 | Update `pyproject.toml` `[tool.coverage.run]` with `parallel = true`, `concurrency = ["multiprocessing", "thread"]`, `sigterm = true`. | pyproject.toml | todo | All four flags required; one missing breaks it. |
| 3 | Local verification per design.md "Verification strategy" — full unit suite, confirm: (a) multiple `.coverage.*` files written, (b) `coverage combine` merges them, (c) reported coverage within ±0.5% of 93% baseline, (d) runtime not >25% slower than pre-canonical. | manual | todo | **Gate**: do not proceed to 3B until this passes. |

### Phase 3B — Workflow changes

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 4 | Update `.github/workflows/tests.yml` "Run tests with coverage" step to use the canonical pattern from design.md. Add `COVERAGE_PROCESS_START` env var. | .github/workflows/tests.yml | todo | Must match the locally-verified command exactly. |
| 5 | Add `scripts/verify_coverage_canonical.sh` that runs the same command locally for future debugging. | scripts | todo | Helps the next debugger reproduce. |
| 6 | Update `tests/unit/ci/test_workflow_yaml.py` if needed. (PR #212's permissive form should already accept either syntax — verify.) | tests | todo | Already-permissive after PR #212. |

### Phase 3C — Verify in CI

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Push PR. Watch CI. **All matrix jobs must pass.** Specifically: ubuntu × {3.10, 3.11, 3.12, 3.13}, macos × {3.10, 3.11, 3.12, 3.13}, windows × {3.10, 3.11, 3.12, 3.13} = 12 jobs. | CI | todo | Lower threshold here would be "regression" — pre-canonical had 1/12 green; canonical with proper setup should be 11+/12. |
| 8 | Coverage XML uploaded to Codecov successfully (was working pre-canonical; verify still working). | CI | todo | |
| 9 | Coverage % reported in CI matches local verification (G5). | manual | todo | |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | Document outcome in `decisions.md` — final config, any mid-execution adjustments, total impact (CI runtime delta, reliability delta). | docs | todo | |
| 11 | Mark spec status `complete` in all 4 .md files. | docs | todo | |
| 12 | Update `docs/COVERAGE_BUG_LOG.md` with the runner-shutdown bug as Class 7 ("xdist + pytest-cov merge OOM under coverage IPC pressure"), and the resolution. | docs | todo | Continues the bug-log dataset (per personal preference / blog post). |

### Failure-to-deliver path

If Phase 3A task #3 (local verification) fails:

1. **Do not push.** This is the "fix it before CI sees it" gate that
   PR #212 violated.
2. Identify which of the 5 design.md pieces is the problem
   (sitecustomize.py not running? coverage files missing? combine
   finding nothing?). Fix locally. Re-verify.
3. If verification still fails after 2 attempts, escalate scope:
   re-read coverage.py docs, check if there's a 6th piece I missed.
4. Worst case: spec status → `partial`, document the dead-end in
   `decisions.md`, evaluate whether `pytest --cov ... --cov-report=`
   (drop term-missing only) is enough relief on its own.

The spec is **complete** when the canonical pattern delivers green
CI on at least 11/12 matrix jobs, no runner-shutdown failures, and
coverage % matches the pre-canonical baseline.
