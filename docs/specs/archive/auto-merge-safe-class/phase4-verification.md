# Phase 4 verification — auto-merge-safe class

This document records the live, end-to-end verification of the
`auto-merge-safe` workflow (`.github/workflows/auto-merge-safe.yml`)
after the `ADMIN_MERGE_TOKEN` secret was provisioned on
2026-06-14.

## What is verified

The verification exercises both directions of the path-class guard
with real pull requests, confirming the mechanism is fail-closed:

- **In-class PR** — every changed path is under `tests/`, `docs/`,
  `.help/`, or is a root-level `*.md`. Expected: the `label` job
  applies the `auto-merge-safe` label, and once the `coverage`
  required check is green the `merge` job admin-squash-merges the
  PR, bypassing only a redundant hung lane.
- **Out-of-class PR** — at least one changed path is outside the
  class (here, a comment-only edit under `src/`). Expected: the
  `label` job does not apply the label, and the `merge` job skips
  the PR on its independent path-class re-check even when
  `coverage` is green.

## This PR

This PR is the in-class case: it adds a single file under `docs/`.
A successful auto-merge of this PR is itself the positive half of
the verification.

## Cross-references

- Class definition: `docs/specs/auto-merge-safe-class/design.md`
- Rejected alternatives:
  `docs/specs/auto-merge-safe-class/decisions.md`
- Guard implementation: `.github/scripts/auto_merge_guard.py`
