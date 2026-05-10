# Spec: Canonical Coverage Pattern for pytest-xdist CI

**Status**: draft
**Created**: 2026-05-10
**Origin**: PR #212 attempted the canonical pattern (commit 2651ce75)
without all the required pieces and made CI worse, not better. The
canonical pattern remains the right destination — this spec scopes
the *complete* setup as its own work item with verification before
push.

---

## Phase 1: Requirements

### Why

`attune-ai`'s CI uses `pytest --cov=src/attune ... -n auto` (pytest-cov
+ pytest-xdist). pytest-cov collects coverage from each xdist worker
via execnet IPC and merges into the master process's memory before
writing XML. With 18,000+ tests across many modules, this merge step
has been observed to:

- Spike memory past GitHub-hosted runner limits (tested theory)
- Take long enough that runner output-buffer pressure builds up
- Manifest as `[100%] PASSED → ##[error] runner shutdown signal` within
  73-117ms — pytest never reaches its summary line, never writes XML

The canonical coverage.py pattern avoids the IPC merge entirely: each
subprocess writes its own `.coverage.<host>.<pid>.<rand>` file
in parallel during test execution; `coverage combine` later reads files
from disk. No master-process memory spike, no IPC bottleneck. This is
the recommended approach in coverage.py docs for parallel test execution.

### What went wrong in PR #212's attempt

Commit 2651ce75 added:
- `[tool.coverage.run] parallel = true, concurrency = ["multiprocessing", "thread"]`
- Workflow command: `coverage run -m pytest -n auto --no-cov ...` then
  `coverage combine && coverage report --fail-under=85 && coverage xml`

What it was *missing*:
- **`COVERAGE_PROCESS_START` env var** — required for subprocess
  instrumentation to actually fire when xdist's workers start. Without
  it, only the main `coverage run` process is instrumented; subprocess
  workers run uncovered, and their data files are never written.
- **`sigterm = true`** in coverage config — without it, coverage
  processes killed by SIGTERM (which xdist uses for worker cleanup)
  don't flush their data; combine sees missing files and fails or
  produces incomplete coverage.
- **A `sitecustomize.py` or `.pth` file** that calls
  `coverage.process_startup()` early in subprocess Python startup —
  required because `COVERAGE_PROCESS_START` only triggers if coverage
  has a chance to bootstrap before user code imports.

Result: ubuntu 3.13 went from 6m9s passing to 27m37s failing with a
23-minute silent gap (workers running uninstrumented and slowly), then
runner shutdown. The pattern was *worse than what it replaced*.

### Goals

- **G1.** Workflow uses canonical `coverage run` + `coverage combine`
  pattern with all required pieces present.
- **G2.** Subprocess workers under pytest-xdist are properly
  instrumented; `coverage combine` finds data files from every worker.
- **G3.** Local verification before push: run the new pattern on a
  representative subset (or full suite) locally, confirm coverage is
  collected from all workers, confirm combine produces a sane number.
- **G4.** CI matrix passes consistently across all platforms (the
  whole point — the runner-shutdown failure mode goes away).
- **G5.** Coverage % reported by the new pattern matches (within ±0.5%)
  the pre-canonical baseline (~93% historically). Regression detection.

### Non-goals

- Not changing the coverage threshold (stays at 85%).
- Not changing xdist worker count strategy (`-n auto` stays).
- Not addressing the unrelated test bugs PR #212's diagnostic exposed
  (TestRecordChoice's real-Redis dependency, etc.). Those land in their
  own follow-up PRs / specs.

### Public API impact

None. This is internal CI tooling. No PyPI consumer sees a behavior
change.
