# Requirements — Recursing-Montalcini Stash Triage

**Status:** draft (2026-05-16)
**Stash:** `stash@{3}` on the local repo (was `stash@{0}` at push time; index drift due to parallel-session stashes pushed after)
**Stash message:** "On claude/recursing-montalcini-0d26be: recursing-montalcini-2026-05-16 WIP (auto-stashed before worktree removal)"

---

## Problem

During 2026-05-16 worktree cleanup, the `recursing-montalcini-0d26be` worktree was flagged as "dirty no-PR, 39 commits behind origin/main." First-pass inspection (`git status` showing 15 modified files) led to the conclusion "stale reversion of shipped work, not salvageable." The worktree was removed after a precautionary `git stash push -u`.

Subsequent stash-drop safety triage revealed the first-pass call was wrong. The stash contains **1374 insertions across 19 files**, including substantive net-new work that does NOT correspond to anything currently on `main`:

| Pattern | Files | Lines |
|---|---|---|
| Pure additions (new files / new content) | 9 | ~822 |
| Modifications (mixed +/-) | 7 | ~445 net add |
| Pure deletions (stale work overwriting shipped state) | 2 | -613 |

The pure-deletion entries (`test_coverage_batch18.py`, `test_coverage_batch5.py`) are clearly the stale-reversion piece — those files were retired on `main` since the worktree was checked out, and applying the stash naively would re-resurrect deleted code. But everything else needs per-file review.

The work appears to span at least four themes:

- **Voice / output**: `src/attune/voice/formatter.py` +147/-2 + `src/attune/workflows/output.py` +208/-372 + a new 202-line `tests/unit/voice/test_formatter.py`. Net effect on `output.py` is -164 lines — looks like a refactor that moved logic into the voice layer.
- **Release agents**: new 135-line `src/attune/agents/release/release_models.py` + `release_prep_team.py` +33/-9.
- **Ops dashboard**: `routes/dashboard.py`, `routes/runner.py`, `runner.py`, `static/css/main.css`, `static/js/run_view.js`, `templates/run_view.html`, plus a new 154-line `tests/unit/ops/test_runner.py`. Some of this may overlap with the Phase 5 work (PR #413) that shipped 2026-05-13.
- **CLI**: `cli_minimal.py` +17/-4, `cli_commands/workflow_commands.py` +89/-5.
- **Infra**: `.claude/CLAUDE.md` +61 (lessons), `.claude/settings.json` +10, `.pre-commit-config.yaml` +17.

## Why this matters

- Throwing the stash away loses real work that someone (possibly me-in-a-prior-session) wrote. Not catastrophic — git history is not the only artifact — but worth a few hours of triage to recover what stands.
- Applying the stash naively to `main` is destructive — it reverts shipped PRs (the -613 lines of deleted tests) and likely conflicts on every modified file (39 commits of drift).
- The composite shape ("4 themes in one stash") means triage has to split the work into multiple PRs along theme boundaries. Single-purpose PRs are the discipline.
- The session that created the stash is unknown; no PR was opened. Author intent has to be reconstructed from the diff content. Some of it may have already shipped under a different code path (e.g. Phase 5's `ATTUNE_REC` infra may have superseded the dashboard work).

## Non-goals

- **Not auto-applying any of the stash.** Every file needs human judgment on keep / superseded / re-do / drop.
- **Not preserving the stash as-is forever.** The goal is to either land the salvageable parts as PRs or document a explicit drop with rationale.
- **Not blocking any other work.** This triage runs at its own pace.

## Success criteria

By the end of this spec:

1. Every one of the 19 files in the stash has a classification: `keep` (apply to a new branch and PR), `superseded` (already shipped in another form, drop), `re-do` (concept is good but needs to be redone against current main), or `drop` (stale, no value).
2. `keep` items are grouped by theme into single-purpose PRs.
3. The original stash is dropped (with a one-line rationale in the closeout commit) OR documented as preserved indefinitely with a specific reason.
4. No regression: any salvaged work passes CI on its own merits, no rebase-then-apply shortcuts.

## Risks

- **Wasting effort on superseded work.** Mitigation: Phase 0 grep-against-main check for each pure-addition file. If a new file with that name already exists on main, skip.
- **Mis-classifying a legitimate work-in-progress as superseded.** Mitigation: when in doubt, classify as `re-do` rather than `drop`. Re-do is conservative; drop is irreversible.
- **Triage exceeding its budget.** Mitigation: hard cap at 1 working session per theme (4 sessions max). If a theme genuinely needs more, it's not "salvage" anymore — it's "new feature on top of an old draft," which is a different decision.

## Open questions

See `decisions.md`.
