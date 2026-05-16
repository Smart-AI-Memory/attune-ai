# Tasks: Deprecated Module Retirement

**Status**: done (2026-05-09) — both removals committed on branch
`retire-deprecated-modules-v7` (commits `41a6dc99`, `18d5e9b0`).
See `decisions.md` execution log for per-commit detail.

---

## Phase 3: Tasks

Two commits, in order. Each row in 3B/3C is a single commit. Phase 3A
runs once up front.

### Phase 3A — Pre-flight

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Cross-repo grep for both module paths across all sibling attune-* repos. Confirm zero hits. | manual | done | Confirmed zero hits across the 8 sibling repos. |
| 2 | Re-confirm baseline: `pytest tests/unit/ -n auto` passes 14,110 (the post-ignored-tests-spec count). | test-infra | done | Baseline confirmed at 14,110 (skipped + xfailed at 81 + 10). |
| 3 | Read `examples/orchestration/basic_usage.py` end-to-end and rewrite against `ReleasePrepTeamWorkflow` (D1 = rewrite). Verify the example runs end-to-end before committing. | docs / src | done | Rewrote Examples 1/2/8; deleted broken Example 3 (test_coverage_boost was already removed). |
| 4 | Establish formal deprecation date for `attune.scaffolding` (G1). | docs / git | done | **2026-02-21** (commit 3833d5d6, PR #60). Module first added 2026-02-01 (fafd4321). See decisions.md. |

### Phase 3B — Module removals

| # | File / Module | Status | Notes |
|---|---|--------|-------|
| 5 | **Commit 1**: Remove `attune.workflows.orchestrated_release_prep`. Delete the module file, edit `src/attune/workflows/__init__.py`, apply D1 to `examples/orchestration/basic_usage.py`. | done | Commit `41a6dc99`. Also trimmed deprecated test classes from `test_coverage_batch6.py` and `test_workflow_consolidation.py`. |
| 6 | **Commit 2**: Remove `attune.scaffolding` package. `git rm -r src/attune/scaffolding/`, edit `pyproject.toml` (source-exclusion, per-file-ignores, coverage omit). | done | Commit `18d5e9b0`. Also removed scaffolding row from `docs/reference/cli-reference.md`. |

### Phase 3C — CHANGELOG and docs

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Add CHANGELOG entry under **v7.0.0** (D2 resolved — couples this with the 100%-coverage release). Two bullets, one per module, each with the migration line verbatim from requirements.md "Public-API impact." | docs | done | Added in CHANGELOG.md under "## [7.0.0] - planned". |
| 8 | Search docs/ for any references to either module and update. Likely candidates: `README.md`, anything under `docs/` mentioning `scaffolding` or release-prep workflows. | docs | done | One hit fixed: `docs/reference/cli-reference.md` (scaffolding row removed). One unrelated hit left: `docs/guides/RELEASE_PREPARATION.md:147` references `/scaffolding/` inside a sample `.gitignore` — refers to a hypothetical top-level dir, not the deleted package. |

### Phase 3D — Validation

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 9 | After Commit 1: full unit suite green; lazy-export sanity `python -c "from attune.workflows import *"` does not raise. | manual | done | 14,103 passed; sanity checks all OK. |
| 10 | After Commit 2: full unit suite green; `python -m attune.scaffolding` exits with `ModuleNotFoundError` (intended terminal state). | manual | done | 14,103 passed (no change from Commit 1); ModuleNotFoundError confirmed. |
| 11 | Final cross-repo re-grep (G3). Same command as task #1, must still return zero hits. | manual | todo | Recommended before pushing the branch; sibling repos move independently. |
| 12 | CHANGELOG entry exists for both modules with migration text (G4). | manual | done | Verified in CHANGELOG.md. |
| 13 | CI parity check after PR lands on main. | CI | todo | Pending: PR not yet opened. Verify after merge. |
| 14 | Append entry to `docs/COVERAGE_BUG_LOG.md` under a new session header: "Class — Bug class 5: deprecated production code outliving its tests." Note both modules and link to this spec. | docs | done | Class 5 added to taxonomy; session-49f entry covers both removals; tally updated. |

### Failure-to-deliver path

If Commit 1 surfaces an unexpected internal caller (Risk 1 or Risk 2):

1. Mark task #5 as **deferred** with the blocker named.
2. Skip to Commit 2 (`attune.scaffolding`) — it's independent.
3. Append blocker details to `decisions.md`: what the caller is, why it
   wasn't caught in Phase 3A, and what production change is needed
   before retirement can complete.
4. Mark spec status as **partial**.

If Commit 2 surfaces a sibling-repo dependency (G3 fails on re-check
in task #11 even though task #1 was clean):

1. Stop. Do not push.
2. The spec's premise (zero external callers within our control)
   is wrong; this becomes a coordination problem, not a removal.
3. Document the dependency in `decisions.md` and pivot to a
   coordinated-release plan across the affected sibling repo.

The spec is **done** when both module trees are gone, the CHANGELOG
names both removals with migration text, and `git grep` returns no
hits for either path across `attune-ai` or any sibling repo.
