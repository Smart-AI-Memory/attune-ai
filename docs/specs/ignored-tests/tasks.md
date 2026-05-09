# Spec: Resolve `--ignore`-d Test Files

**Status**: approved

---

## Phase 3: Tasks

### Phase 3A — Setup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Create `docs/specs/ignored-tests/decisions.md` as an empty file with a one-line header. Each per-file resolution will append a paragraph here. | docs | todo | Append-only log; lives alongside the spec. |
| 2 | Capture the **current** baseline: full unit suite green count under `-n auto`. Record in this spec as the reference number for Phase 3D regression checks. | test-infra | todo | Expected ~14,075 passed (2026-05-09 baseline). Re-run before starting in case anything has drifted. |

### Phase 3B — Per-file resolution

Each row below is a single commit. Order matches design.md
recommendation. Re-confirm the classification (column "Path")
against the file before starting — initial classifications come
from the test-infrastructure audit and may need revision.

| # | File | Path | Status | Notes |
|---|------|------|--------|-------|
| 3 | `tests/unit/workflows/test_orchestrated_release_prep.py` (5/35 fail) | **R1 REPAIR** | todo | Sample root cause from audit: `assert isinstance(result, AgentResult)` fires at `core_strategies.py:161` because real workflow execution returns non-`AgentResult`. Group all 5 failures by root cause first; if > 3 distinct causes, re-classify to R2. |
| 4 | `tests/unit/models/test_execution_and_fallback_architecture.py` (41/52 fail) | **R3 RETIRE (with salvage)** | todo | File is explicit about being aspirational ("Coverage Target: 95%+ from 21-73%") and admits drift in code comments (`# NOTE: FallbackPolicy may not exist or have different API - Gap 3.2`). Salvage pass: walk the 8 invariants in the docstring; for each, check current production + check whether tested elsewhere. Write a small targeted file for any unique surviving invariants. |
| 5 | `tests/unit/scaffolding/test_scaffolding_cli.py` (28/42 fail) | **R3 RETIRE (with salvage)** | todo | Re-classify after reading `src/attune/scaffolding/cli.py`. Heavy `sys.modules` mocking (`sys.modules["test_generator"] = MagicMock()`) is the smell — mocks have lost their target. If `cli.py` is small enough to test cleanly without sys.modules surgery, downgrade to R2 RECONCILE and rewrite. |
| 6 | `tests/unit/orchestration/test_composition_patterns.py` (14/35 fail) | **R2 RECONCILE** | todo | First task: disambiguate (a) test-debt-only vs (b) production-regression. Method: `git log --oneline --since=2026-01-24 -- src/attune/orchestration/` and same for the test file. The "XFAIL TEST REMEDIATION - COMPLETED (2026-01-24)" header is the diagnostic. |

### Phase 3C — pytest.ini cleanup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | After each per-file commit (#3–#6) lands, remove the corresponding `--ignore=tests/unit/...` line from `pytest.ini`. | pytest.ini | todo | Done as part of each per-file commit, not a separate commit. |
| 8 | After all four files are resolved, update the explanatory comment block in `pytest.ini` (currently lines 29–39) to remove the audit findings and replace with a one-line note: "Only `--ignore=tests/integration/` remains — integration tests live behind their own runner. See `docs/specs/ignored-tests/`." | pytest.ini / docs | todo | Keep the comment short — it's history, not active context. |

### Phase 3D — Validation

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 9 | After each per-file commit, run `pytest tests/unit/ -n auto` and confirm: (a) the resolved file's tests now pass (or are deleted), (b) total green count is ≥ the baseline from #2, (c) zero new failures elsewhere. | manual | todo | Required before pushing each commit. Catches xdist interference (Risk 4). |
| 10 | Final-state check: `grep -E "^\s*--ignore=tests/unit" pytest.ini` returns nothing. | manual | todo | Trivial but the canonical "are we done?" command. |
| 11 | Final-state check: `git grep -n "import .*orchestrated_release_prep\|import .*composition_patterns\|import .*execution_and_fallback_architecture\|import .*scaffolding/cli" tests/` returns no broken imports from sibling test files. | manual | todo | If we deleted a test file that another file imported helpers from, this catches it. |
| 12 | Update `docs/specs/test-infrastructure/tasks.md` task #10: change status from **deferred** → **done**, link to this spec's decisions.md. | docs | todo | Closes the loop with the parent spec. |
| 13 | CI parity check: confirm CI runs are still green after the merged commits land on `main`. | CI | todo | Test debt resolution shouldn't affect CI behavior, but the sweep itself is the kind of thing that surfaces hidden coupling. |

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
