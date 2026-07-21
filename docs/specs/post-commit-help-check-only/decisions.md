# Post-Commit Help Check-Only — Decisions

**Status:** shipped (2026-07-20) — D1 implemented same day in
#1532; drift-guard tests landed with it.

## 2026-07-20 — Spec approved; D1 ruled: option A (chair: Patrick)

Approved in the chair-rulings sitting (stepped-through review).
Premise re-verified live before the ruling: `run_hook`
(`src/attune/help/maintenance.py`) still calls `run_maintenance`
WITHOUT `dry_run`, so the per-commit whole-feature LLM re-polish
the spec targets remains active on the post-commit path.

**D1 — RULED: option A (dry-run flip).** `run_hook` passes
`dry_run=True`; the existing `stale_count > 0` warning branch
("N feature(s) are stale — run /coach maintain") is the surviving
behavior; the regenerated-count branch becomes dead code and is
removed. Option B (a `regenerate: bool = False` param) declined —
the spec's grep found no caller wanting per-commit regen, and the
no-hook-spend policy (polish-cost-reduction lever 1) argues for
removing the path outright rather than parameterizing it.

Validation per the spec: unit test asserting
`regenerated_count == 0` and no template files written; a
drift-guard regression test so the regen path cannot silently
return; the stale pre-commit-hook lesson in `.claude/lessons.md`
corrected to name the real surface as part of the close-out.
## 2026-07-20 — Shipped (#1532): execution evidence

- Unit: `run_hook` with a stubbed generator asserts
  `regenerated_count == 0`, generator never called, template
  bytes unchanged, and the hook emits the stale warning
  (`tests/unit/help/test_maintenance.py`,
  `tests/unit/hooks/test_help_hooks.py`).
- Drift guard: both suites include a test whose generator stub
  RAISES if the post-commit path ever reaches the regenerating
  branch, so the per-commit LLM re-polish cannot silently return.
- The hook's `regenerated_count > 0` "auto-updated" branch became
  dead code and was removed; the surviving behavior is the
  `stale_count > 0` stderr warning ("N feature(s) are stale — run
  /coach maintain").
- Close-out: the stale lesson blaming the PRE-commit hook was
  corrected in `.claude/lessons.md` (and its CLAUDE.md core
  mirror) to name the post-commit surface and record the fix.
