# Post-Commit Help Check-Only — Decisions

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
