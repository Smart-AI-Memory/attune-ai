# Decisions — CI gating-lane isolation

**Status:** draft

Append-only log. See `requirements.md` for the problem framing.

---

## Context that motivated the spec (2026-06-15)

Opened after QA #6 (the omit-audit conversion run) where the
runner-hang on the `coverage` and `clock-tz`/Windows lanes blocked
auto-merge on nearly every PR (#892–#894, #901, #904), each needing
manual `gh run cancel` / `gh run rerun --failed` and, on #904, an
admin-merge on a hung `coverage` (justified by `test (ubuntu 3.12)`
being green — same suite — and the diff being coverage-only-additive).

The pre-existing `auto-merge-safe.yml` D7 retry fix (this session)
handles the *concurrent-merge race* but NOT the *hang-blocks-trigger*
problem — that needs the topology change proposed here.

## Open decisions (to resolve in design)

- **D1 — layering order.** Proposed: A (timeouts+retry) → B (gate/matrix
  split) → C (coverage shard) only if needed. _Pending ratification._
- **D2 — retry mechanism.** `nick-fields/retry` action vs a pure-shell
  re-invoke (no third-party action, consistent with
  ci-matrix-right-sizing's "no third-party action" preference).
  _Pending._
- **D3 — branch-protection migration.** How to flip required contexts
  to the `Gate` workflow's job names without a "missing required check"
  window. Likely: add new contexts as non-required, prove they emit,
  then swap. _Pending._
