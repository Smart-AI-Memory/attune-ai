# Auto-Merge-Safe Class — Tasks

**Status:** complete — auto-merge-safe class working end-to-end (#881);
`.github/workflows/auto-merge-safe.yml` live. Reconciled from stale
"in progress (2026-06-14)" and archived 2026-06-24.

---

## Phase 1 — Guard + tests (verifiable without the PAT)

- [x] T1 — `.github/scripts/auto_merge_guard.py` (pure function +
  CLI, fail-closed).
- [x] T2 — `tests/unit/github_scripts/test_auto_merge_guard.py`
  (importlib-loaded; covers in-class dirs, root `*.md`, `src/`
  rejection, `.github/` rejection, rename previous-path, `..`
  traversal, empty set).
- [x] T3 — Guard tests pass locally (33 passed).

## Phase 2 — Workflow

- [x] T4 — `.github/workflows/auto-merge-safe.yml` (label job +
  merge job per design).
- [x] T5 — Pre-create the `auto-merge-safe` label.

## Phase 3 — Land

- [ ] T6 — PR; CI green; merge.

## Phase 4 — Verify end-to-end (needs `ADMIN_MERGE_TOKEN`)

- [ ] T7 — Patrick creates the fine-grained PAT secret.
- [ ] T8 — Throwaway test-only PR auto-merges on coverage-green.
- [ ] T9 — Deliberately `src/`-touching PR is NOT merged (label
  withheld / merge job skips).
