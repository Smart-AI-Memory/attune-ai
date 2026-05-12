# Spec: Resolve `--ignore`-d Test Files

**Status**: complete (2026-05-09 — see `decisions.md`)

---

## Phase 3: Tasks

### Phase 3A — Setup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Create `docs/specs/ignored-tests/decisions.md` as an empty file with a one-line header. Each per-file resolution will append a paragraph here. | docs | **done** | Populated 2026-05-09 with all four per-file rationale entries. |
| 2 | Capture the **current** baseline: full unit suite green count under `-n auto`. Record in this spec as the reference number for Phase 3D regression checks. | test-infra | **done** | Baseline 14,075 passed → final 14,110 passed (+35 recovered from composition reconcile). |

### Phase 3B — Per-file resolution

Each row below is a single commit. Order matches design.md
recommendation. Re-confirm the classification (column "Path")
against the file before starting — initial classifications come
from the test-infrastructure audit and may need revision.

| # | File | Path | Status | Notes |
|---|------|------|--------|-------|
| 3 | `tests/unit/workflows/test_orchestrated_release_prep.py` (5/35 fail) | **R3 RETIRE** (reclassified from R1) | **done** | Commit `f88afb08`. Reclassified after reading production: module is deprecated since v5.2.0 ("Remove in v6.0"); replacement `ReleasePrepTeamWorkflow` already has parallel coverage. File deleted, no salvage. See decisions.md. |
| 4 | `tests/unit/models/test_execution_and_fallback_architecture.py` (41/52 fail) | **R3 RETIRE — no salvage** | **done** | Commit `90d33dce`. All 8 invariant categories already covered elsewhere (registry, executor, fallback, circuit breaker, cost tracking, routing, telemetry). File deleted. |
| 5 | `tests/unit/scaffolding/test_scaffolding_cli.py` (28/42 fail) | **R3 RETIRE — no salvage** | **done** | Commit `b343fcbd`. Production CLI is deprecated (emits notice on every invocation); already excluded from coverage. Mock-driven tests had lost their targets. File deleted. |
| 6 | `tests/unit/orchestration/test_composition_patterns.py` (14/35 fail) | **R2 RECONCILE** (confirmed) | **done** | Commit `fd80a8d0`. Single-fixture fix in `tests/unit/orchestration/conftest.py`: patch `ExecutionStrategy._execute_agent` at the class level so nested ParallelStrategy in DebateStrategy inherits the mock. All 35 tests now pass; no test method touched. |

### Phase 3C — pytest.ini cleanup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | After each per-file commit (#3–#6) lands, remove the corresponding `--ignore=tests/unit/...` line from `pytest.ini`. | pytest.ini | **done** | Folded into each per-file commit. |
| 8 | After all four files are resolved, update the explanatory comment block in `pytest.ini` (currently lines 29–39) to remove the audit findings and replace with a one-line note: "Only `--ignore=tests/integration/` remains — integration tests live behind their own runner. See `docs/specs/ignored-tests/`." | pytest.ini / docs | **done** | Comment block in `pytest.ini` now points at this spec. |

### Phase 3D — Validation

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 9 | After each per-file commit, run `pytest tests/unit/ -n auto` and confirm: (a) the resolved file's tests now pass (or are deleted), (b) total green count is ≥ the baseline from #2, (c) zero new failures elsewhere. | manual | **done** | Recorded inline in each commit; final count 14,110 passed. |
| 10 | Final-state check: `grep -E "^\s*--ignore=tests/unit" pytest.ini` returns nothing. | manual | **done** | Verified 2026-05-12 — no matches. |
| 11 | Final-state check: `git grep -n "import .*orchestrated_release_prep\|import .*composition_patterns\|import .*execution_and_fallback_architecture\|import .*scaffolding/cli" tests/` returns no broken imports from sibling test files. | manual | **done** | Verified 2026-05-12 — no matches. |
| 12 | Update `docs/specs/test-infrastructure/tasks.md` task #10: change status from **deferred** → **done**, link to this spec's decisions.md. | docs | **done** | Commit `e872eae9`. Parent spec marked complete. |
| 13 | CI parity check: confirm CI runs are still green after the merged commits land on `main`. | CI | **done** | All commits merged; main is clean and green as of `bb0d8aec` (2026-05-12). |

### Failure-to-deliver path

If any file's resolution exceeds the per-file budget (rough cap:
1 day of focused work) because a fix needs production-code change
beyond test-side repair:

1. Mark that file's row in Phase 3B as **deferred** with the blocker
   named in the Notes column.
2. Leave its `--ignore` line in `pytest.ini` (Phase 3C task #7
   becomes partial).
3. Append the blocker to `docs/specs/ignored-tests/decisions.md`
   under that file's note, including: what the blocker is, what
   production code needs to change, and an estimate of effort.
4. Continue with the remaining files.
5. Mark the spec status as **partial** (not deferred — partial
   means some files resolved, some still pending).

The spec is **done** when all four `--ignore=tests/unit/...` lines
are gone from `pytest.ini` and `decisions.md` has a paragraph for
each file describing what happened to it.
