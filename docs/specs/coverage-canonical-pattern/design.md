# Design: Canonical Coverage Pattern

**Status**: draft

---

## Phase 2: Design

### Approach

Five small artifacts, each landing as its own commit on a single PR:

1. **Bootstrap file** — a project-root `sitecustomize.py` (or `.pth`
   file approach) that calls `coverage.process_startup()` so
   subprocess Python interpreters bootstrap with coverage active when
   `COVERAGE_PROCESS_START` is set. This is the *missing piece* from
   PR #212's attempt.

2. **`pyproject.toml` `[tool.coverage.run]` config**:
   ```toml
   parallel = true
   concurrency = ["multiprocessing", "thread"]
   sigterm = true
   data_file = ".coverage"
   ```

3. **`.coveragerc` or use `pyproject.toml`** as the
   `COVERAGE_PROCESS_START` target. coverage.py supports both;
   `pyproject.toml` is preferred since it's already the source of
   truth.

4. **Workflow change** in `.github/workflows/tests.yml`:
   ```yaml
   - name: Run tests with coverage
     env:
       COVERAGE_PROCESS_START: ${{ github.workspace }}/pyproject.toml
     run: |
       coverage erase
       coverage run -m pytest -n auto --no-cov \
         --timeout=60 --timeout-method=thread \
         -m "not network and not integration"
       coverage combine
       coverage report --fail-under=85
       coverage xml
   ```

5. **Local verification script** at
   `scripts/verify_coverage_canonical.sh` that runs the same command
   locally so devs (and the next CI debugger) can reproduce. Catches
   environment drift between local and CI.

### Why each piece is needed

| Piece | Without it | With it |
|---|---|---|
| `sitecustomize.py` calling `coverage.process_startup()` | Subprocess workers (xdist's gw0..gwN) never bootstrap coverage. Data files aren't written. Combine finds nothing. | Workers bootstrap coverage during Python startup. Each writes its own `.coverage.<host>.<pid>.<rand>`. |
| `parallel = true` | Workers stomp on each other's `.coverage` file. | Each worker writes a uniquely-named file. |
| `concurrency = ["multiprocessing", "thread"]` | Coverage doesn't know to instrument subprocess/thread spawns. Misses data created in those contexts. | Coverage's multiprocessing/thread patches activate, instrumenting forks/spawns. |
| `sigterm = true` | Workers killed by SIGTERM (xdist cleanup) lose buffered data. Combine sees gaps. | SIGTERM handler flushes data file before exit. |
| `COVERAGE_PROCESS_START` env var | Even with sitecustomize.py, `coverage.process_startup()` is a no-op without this env var pointing at config. | Triggers actual startup. |
| `--no-cov` on pytest | pytest-cov plugin double-instruments and competes with `coverage run`. | pytest-cov is loaded but inactive; `coverage run` owns instrumentation. |

Five separate moving parts, all required, none optional. PR #212's
attempt had pieces 2 and 4 only — explains why it broke things.

### Bootstrap file: `sitecustomize.py` vs `.pth`

Two ways to trigger subprocess startup:

**Option A** — project-root `sitecustomize.py`:
```python
"""Coverage bootstrap for subprocess workers (pytest-xdist + coverage.py).

Runs before any user code in subprocess Python interpreters when this
file is on sys.path. Combined with COVERAGE_PROCESS_START env var, it
triggers coverage instrumentation in xdist worker subprocesses.

See docs/specs/coverage-canonical-pattern/.
"""
import coverage
coverage.process_startup()
```

**Option B** — a `.pth` file installed by the test harness. More
fragile (depends on site-packages location) but doesn't require
`sitecustomize.py` to be on sys.path.

**Decision: Option A.** `sitecustomize.py` at the project root is on
sys.path during pytest runs (pytest adds the project root). It's also
explicit and discoverable for future contributors.

### Verification strategy

**Local**, before pushing the PR:

1. Install fresh: `pip install -e .[dev]`
2. Run the same command CI will run:
   ```bash
   COVERAGE_PROCESS_START=$(pwd)/pyproject.toml \
     coverage erase && \
     COVERAGE_PROCESS_START=$(pwd)/pyproject.toml \
     coverage run -m pytest tests/unit/ -n auto --no-cov \
       --timeout=60 --timeout-method=thread \
       -m "not network and not integration" && \
     coverage combine && \
     coverage report
   ```
3. Confirm:
   - Multiple `.coverage.*` files exist before combine
     (`ls -la .coverage*`)
   - `coverage combine` reports merging multiple files (one per worker)
   - `coverage report` shows ~93% (matching pre-canonical baseline)
   - Total runtime is comparable to pre-canonical (not 4-5x slower
     like PR #212's broken attempt)

If any of these fail locally, **do not push**. The bug is fixable
before it ever hits CI.

### Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Local verification passes but CI fails differently. | Pre-flight gate: only push when local matches expected output. CI then verifies cross-platform. |
| 2 | `sitecustomize.py` conflicts with another project-root file or with pytest's path manipulation. | Test locally first. If conflict, switch to Option B (`.pth` file). |
| 3 | Coverage % differs by more than 0.5% from baseline. | Investigate before merging — usually means one of the pieces is incomplete. |
| 4 | Subprocess instrumentation slows tests significantly even when working correctly. | Acceptable up to ~25% slowdown (still faster than the broken pattern). If beyond that, evaluate `concurrency = ["multiprocessing"]` only (drop "thread"). |
| 5 | `sigterm = true` interacts badly with pytest-timeout's signal handling. | Local verification catches this; if it surfaces, switch timeout method or accept that some teardown coverage is lost. |

### Decisions to make at execution time

- **D1.** Coverage data files location — default `.coverage*` in repo
  root vs explicit `.coverage_data/` directory (cleaner but requires
  more config). Default unless local verification suggests otherwise.
- **D2.** Whether to keep `--cov-report=term-missing` for local-dev
  ergonomics. Likely yes (just don't pass it to `coverage report`
  in CI, since CI doesn't read terminal output anyway).
