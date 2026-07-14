# Post-Commit Help Maintenance → Check-Only

**Status:** draft — awaiting review; recommitted at 2026-07-14 triage
**Owner:** Patrick + agent
**Created:** 2026-06-22

---

## Premise correction (verify-first)

A standing lesson said *"the `.help` regen pre-commit hook does a full
LLM re-polish of a feature's whole help corpus on any source touch,
leaving stash-and-reappear files."* That is now **stale**: the
**pre-commit** path was fixed by the polish-cost-reduction spec (lever
1, ratified 2026-06-10) —

- `scripts/regenerate_help_templates.py` is **check-only** (warns which
  features lag; never regenerates, never spends LLM).
- `scripts/check_docs_freshness.py` is **warn-only** unless
  `ATTUNE_DOCS_AUTOREGEN=1`.

But the problem still *exists* on a different path, which is why
`.help/templates/plugin/{concept,reference,task}.md` got rewritten in
the working tree during the 8.7.1 ship (the release commit touched
`plugin/core/__init__.py`):

- **`plugin/hooks/help_post_commit.py`** (a PostToolUse hook on `git
  commit`) calls `attune.help.maintenance.run_hook(...)`, which calls
  `run_maintenance(...)` **in regenerate mode** — LLM-re-polishing every
  affected feature's templates and dropping them in the working tree.

So the per-commit whole-feature re-polish — the exact repeat-API-spend
+ hallucination-risk + stash-and-reappear churn lever 1 eliminated for
the pre-commit path — is **still live on the post-commit path**, and
inconsistent with the ratified policy ("polish-bearing regen happens at
release-prep cadence, not per-commit").

---

## Goals

1. The post-commit hook becomes **check-only**: detect + warn which
   features are stale after a commit; **never** auto-regenerate, spend
   LLM budget, or write to the working tree.
2. Behavior matches the pre-commit hooks and the polish-cost-reduction
   policy — polish-bearing regen happens only at release-prep
   (`attune-author regenerate` / `/coach maintain`).
3. Retire/correct the stale lesson so it names the real (now-fixed)
   surface.

## Non-goals

- Removing the post-commit hook entirely (the *warning* is useful).
- Changing release-prep regeneration.

---

## Design sketch

The check-only capability **already exists** — `run_maintenance(...)`
takes `dry_run: bool` ("If True, report staleness without
regenerating"). `run_hook()` currently calls it **without** `dry_run`.

Two clean options:

**A — Flip the hook to dry-run (recommended, smallest).** Have
`help_post_commit.py` (or `run_hook`) pass `dry_run=True`, so the
post-commit path only reports staleness. The hook's existing
`stale_count > 0` / `regenerated_count == 0` branch already prints the
right "N feature(s) are stale — run /coach maintain" warning; the
regenerated-count branch becomes dead and is removed.

**B — Add a `regenerate: bool = False` param to `run_hook`.** Same
effect, explicit at the entry point; lets a deliberate caller still
regenerate. Slightly more surface.

**Recommendation: A** — matches lever 1's "hooks never spend LLM"
stance and removes a now-misleading code path. Reserve B if there's a
real non-release caller that wants regen (none known).

## Validation

- Unit: `run_hook` with affected features + a stubbed generator →
  assert `regenerated_count == 0` and no template files written
  (dry-run), warning emitted.
- Regression guard: a test asserting the post-commit hook path does not
  call the regenerating branch (drift guard, so this can't silently
  come back).
- Manual: commit a change touching a feature's source glob → confirm
  only a stderr warning, no `.help/templates/<feature>/` diff.

## Close-out

- Update `.claude/lessons.md`: correct the stale pre-commit-hook lesson
  to point at the post-commit hook + record the fix.

## Open questions

- **D1**: approve A (dry-run flip) vs B (param)?
- Is there any caller of `run_hook`/`run_maintenance` that *wants*
  per-commit regen? (Grep found only the post-commit hook.)
