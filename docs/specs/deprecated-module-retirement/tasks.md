# Tasks: Deprecated Module Retirement

**Status**: draft

---

## Phase 3: Tasks

Two commits, in order. Each row in 3B/3C is a single commit. Phase 3A
runs once up front.

### Phase 3A — Pre-flight

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Cross-repo grep for both module paths across all sibling attune-* repos. Confirm zero hits. | manual | todo | Command in design.md "Verification strategy" #4. If any hit found, pause and triage before proceeding. |
| 2 | Re-confirm baseline: `pytest tests/unit/ -n auto` passes 14,110 (the post-ignored-tests-spec count). | test-infra | todo | Drift since 2026-05-09 is fine; record actual baseline number for Phase 3D regression checks. |
| 3 | Read `examples/orchestration/basic_usage.py` end-to-end and rewrite against `ReleasePrepTeamWorkflow` (D1 = rewrite). Verify the example runs end-to-end before committing. | docs / src | todo | D1 resolved 2026-05-09 — see decisions.md. |
| 4 | Establish formal deprecation date for `attune.scaffolding` (G1). | docs / git | done | **2026-02-21** (commit 3833d5d6, PR #60). Module first added 2026-02-01 (fafd4321). See decisions.md. |

### Phase 3B — Module removals

| # | File / Module | Status | Notes |
|---|---|--------|-------|
| 5 | **Commit 1**: Remove `attune.workflows.orchestrated_release_prep`. Delete the module file, edit `src/attune/workflows/__init__.py` (lines 76, 157, 160), apply D1 to `examples/orchestration/basic_usage.py`. | todo | After edit, run verification checklist #1–#3 from design.md. |
| 6 | **Commit 2**: Remove `attune.scaffolding` package. `git rm -r src/attune/scaffolding/`, edit `pyproject.toml` (source-exclusion, per-file-ignores, coverage omit). | todo | After edit, run verification checklist #1–#3 from design.md plus `ruff check`. |

### Phase 3C — CHANGELOG and docs

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Add CHANGELOG entry under **v7.0.0** (D2 resolved — couples this with the 100%-coverage release). Two bullets, one per module, each with the migration line verbatim from requirements.md "Public-API impact." | docs | todo | Don't cut v7.0.0 until coverage push completes; let other v7.0 candidates accumulate in the same bucket. |
| 8 | Search docs/ for any references to either module and update. Likely candidates: `README.md`, anything under `docs/` mentioning `scaffolding` or release-prep workflows. | docs | todo | `git grep -n "attune\.scaffolding\|orchestrated_release_prep" docs/ README.md` — read each hit, edit or remove. |

### Phase 3D — Validation

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 9 | After Commit 1: full unit suite green; lazy-export sanity `python -c "from attune.workflows import *"` does not raise. | manual | todo | |
| 10 | After Commit 2: full unit suite green; `python -m attune.scaffolding` exits with `ModuleNotFoundError` (intended terminal state). | manual | todo | |
| 11 | Final cross-repo re-grep (G3). Same command as task #1, must still return zero hits. | manual | todo | Sibling repos may have moved between Phase 3A and now. |
| 12 | CHANGELOG entry exists for both modules with migration text (G4). | manual | todo | Trivial check, do it anyway. |
| 13 | CI parity check after PR lands on main. | CI | todo | If CI fails specifically on the lazy-import map or example file, that's the signal that Risk 2 or D1 was misjudged. |
| 14 | Append entry to `docs/COVERAGE_BUG_LOG.md` under a new session header: "Class — Bug class 5: deprecated production code outliving its tests." Note both modules and link to this spec. | docs | todo | Continues the bug-log dataset (per personal preference for the upcoming blog post). Worth flagging as a *fifth* class — distinct from Class 1/2/3/4 because the code wasn't crashing or unreachable; it was simply orphaned. |

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
