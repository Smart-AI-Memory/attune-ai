# Spec: Test Infrastructure Reliability

**Status**: draft

---

## Phase 2: Design

### Architecture

The fix is split into **diagnose → decide → implement** because the
single load-bearing decision (whether to re-enable pytest-xdist) hinges
on a root cause that hasn't been investigated. The current `pytest.ini`
comment

> `# NOTE: Parallel execution disabled due to import timing issues with workflows package`

is the only artifact of the decision. The original symptom, the affected
module, and whether it still reproduces are all unknown.

```
Phase 2A: DIAGNOSE                  ← read-only investigation
   │
   ├─ Reproduce the historical xdist failure
   ├─ Locate the workflows-package import timing issue
   └─ Profile memory growth in single-process mode
   │
   ▼
Phase 2B: DECIDE                    ← architectural choice
   │
   ├─ Path A: Fix the import issue, re-enable xdist
   ├─ Path B: Fix memory growth, keep -n 0 viable
   └─ Path C: Both (xdist for parallelism, fix imports for safety)
   │
   ▼
Phase 2C: IMPLEMENT                 ← see tasks.md
   │
   ├─ Resolve the three `--ignore`-d test files
   ├─ Address pubsub_direct.py slowness
   └─ Retire scripts/clean_test_artifacts.sh + scripts/run_tests_chunked.sh
```

### Phase 2A — Diagnose

#### D1. Reproduce the xdist failure

Temporarily flip `pytest.ini` `-n 0` to `-n auto`, run the full suite,
capture the failure. Possible outcomes:

- **Tests fail with import errors.** Dump the failing imports; specific
  modules implicate which `src/attune/workflows/__init__.py` initialization
  step has ordering dependencies.
- **Tests fail with race conditions.** Module-level mutable state being
  written from multiple workers. Implicates which globals need to move.
- **Tests pass.** The historical issue has been fixed by some unrelated
  change — the comment in `pytest.ini` is now stale. Just remove the
  workaround.

The investigation output is a written diagnosis with file:line citations.

#### D2. Inspect `src/attune/workflows/__init__.py`

The import-timing comment specifically names the workflows package.
Likely culprits to look for:

- `__init__.py`-level singleton construction (any `_instance = ...` at
  module scope where construction has side effects)
- Cross-module imports that cycle through the workflows package
- Any `import` inside a function body that's there *because* a top-level
  import would deadlock (load-bearing comments worth grepping for:
  `# avoid circular import`, `# import here for ordering`, `# delayed import`)
- Auto-discovery / plugin-loading at import time

Output: a "what currently runs at workflows-package import time"
diagram, with side-effects annotated.

#### D3. Memory profile a single-process run

Run a chunked subset under memory tracing
(`python -X tracemalloc=10 -m pytest tests/...`) capturing the top
allocation sites. Identify whether memory growth is:

- **Pytest plugin overhead** (some plugins keep references to every
  collected test → blocking GC)
- **Fixture leaks** (session-scope fixtures holding heavy objects)
- **Module-level state** (test imports loading data that's never freed)
- **Genuinely unavoidable** (5000 tests × intrinsic cost)

Output: top-10 allocation report and a recommendation on whether
memory growth is fixable independently of xdist.

### Phase 2B — Decide

Post-diagnosis, choose a path:

**Path A — Fix imports, re-enable xdist.** Best if D1 reveals a concrete
fixable issue and D3 shows memory growth is dominated by per-process
overhead that xdist would amortize across workers.

- Pros: Single command, fast, matches CI behavior more closely.
- Cons: Requires understanding the workflows-package import order;
  may surface latent test interdependencies.

**Path B — Fix memory growth, keep `-n 0`.** Best if D1 shows the
xdist issue is a real architectural problem and D3 identifies a
specific leak that, once plugged, makes single-process runs viable.

- Pros: No risk of new concurrency bugs.
- Cons: Slower than parallel; doesn't match CI; vulnerable to future
  test additions pushing memory back over the threshold.

**Path C — Both.** Path A for parallelism *and* Path B for safety.
Best if D1 reveals an issue and D3 reveals a leak; addressing both
gives the most resilient outcome.

The decision is informed by what diagnosis finds, not chosen up front.

### Phase 2C — Implement

Specifics depend on Phase 2B's path. See `tasks.md` for the cross-path
work (the `--ignore` cleanup, the slow file, the workaround retirement).

### Out-of-scope cross-references

- **Coverage data corruption** is already handled by
  `scripts/clean_test_artifacts.sh`. Phase 2C makes that script
  unnecessary by addressing the root cause (xdist data-file collisions
  + lack of automatic cleanup), but the script can stay until then.
- **The full-suite OOM** is mitigated for now by
  `scripts/run_tests_chunked.sh`. Same retirement timing.
- **CI workflow changes** are out of scope per requirements.md non-goals.

### Failure-to-deliver fallback

If diagnosis (D1–D3) takes longer than ~2 days of focused work or
reveals a fix that's prohibitively expensive (e.g. requires a full
workflows-package architectural change), the fallback is:

- Document the workflow with the workarounds as the supported path
  in `CONTRIBUTING.md` (already done).
- Add CI-equivalent runs to a Makefile target (`make test-ci-equivalent`)
  that uses chunked runner under the hood but presents as a single
  command.
- Mark this spec as **deferred** rather than complete, with the
  diagnosis findings preserved as input for a future attempt.
