# Auto-Merge-Safe Class — Design

**Status:** approved (2026-06-14)

---

## Components

| File | Role |
|------|------|
| `.github/scripts/auto_merge_guard.py` | Path-class guard. Pure function + CLI. Fail-closed. |
| `.github/workflows/auto-merge-safe.yml` | Label job (PR events) + merge job (check_run events). |
| `tests/unit/github_scripts/test_auto_merge_guard.py` | Unit tests for the guard (importlib-loaded, repo convention). |

The guard lives under `.github/` on purpose: `.github/` is
out-of-class, so a PR that edits the guard or workflow can never
satisfy the path filter and can never self-auto-merge.

---

## Path-class guard

`is_in_class(path)` is True iff:

- `path` startswith one of `tests/`, `docs/`, `.help/`, **or**
- `path` is a root-level markdown file (`.md`, no `/` in path).

`is_safe_change(paths)` returns `(safe, offending)`:

- empty `paths` => `(False, [])` (fail-closed; nothing to merge
  is suspicious).
- any path with a `..` segment => unsafe (traversal defense).
- safe iff every path `is_in_class`.

CLI: paths via argv or stdin (one per line); exit 0 = safe,
exit 1 = unsafe (prints offending paths).

The workflow feeds the guard the union of each changed file's
`filename` **and** `previous_filename` (so a rename out of `src/`
is caught).

---

## Workflow triggers and jobs

```yaml
on:
  pull_request_target:
    types: [opened, synchronize, reopened, ready_for_review]
  check_run:
    types: [completed]
```

### Job `label` (if event == pull_request_target)

- Permissions: `pull-requests: write`, `contents: read`.
- Token: `GITHUB_TOKEN` (no PAT — labels only).
- Steps: author == `silversurfer562`? fetch PR files (paginated);
  run guard over filename+previous_filename; if safe add
  `auto-merge-safe`, else remove it if present.

### Job `merge` (if event == check_run, name == coverage, conclusion == success)

- Permissions: `contents: write`, `pull-requests: write`.
- Token: `ADMIN_MERGE_TOKEN` (fine-grained admin PAT) for the
  merge; reads can use the same.
- Steps, per open PR for the check_run head SHA (base == main):
  1. author == `silversurfer562`, not draft, head repo == base
     repo — else skip.
  2. labels contain `auto-merge-safe` — else skip.
  3. fetch PR files; run guard — else skip (defense in depth vs a
     hand-applied label).
  4. re-confirm `coverage` == `success` on PR head — else skip.
  5. `gh pr merge <n> --squash --admin --delete-branch`
     (idempotent: skip if not open).

Concurrency keyed per head SHA prevents double-merge races. The
merge job never checks out PR code — pure API calls — so
`pull_request_target` / `check_run` running with base secrets is
safe.

---

## Why `check_run` (not `workflow_run`) for the merge trigger

`coverage` is a job in the **Tests** workflow. Triggering on
`check_run: completed` filtered to `name == 'coverage'` reacts
the instant coverage goes green, regardless of whether the
redundant `test (ubuntu-latest, 3.12)` sibling lane is still hung
— which is precisely the gap. `workflow_run` would wait for the
entire Tests run (including the hung lane's timeout) to complete.

---

## One-time setup (human)

- Patrick creates the fine-grained PAT and stores it as
  `ADMIN_MERGE_TOKEN`. Until then the merge job is inert (it has
  no credential and will no-op/fail-closed).

The `auto-merge-safe` label is pre-created (one-time) so the
label job can add it without `issues: write`.
