# Decisions — Recursing-Montalcini Stash Triage

**Status:** draft (2026-05-16) — no decisions resolved yet

---

## Pre-committed decision matrix (per-file)

The matrix is applied to EACH file in the stash independently. Committed BEFORE Phase 1 inspection runs so judgment doesn't drift from intent.

| Per-file finding | Classification |
|---|---|
| File doesn't exist on `main` AND the stash adds it as a net-new file | `keep` (unless content is obviously broken or duplicates a renamed file) |
| File exists on `main` AND the stash diff makes sense against the current content | `keep` (apply to new branch, resolve conflicts) |
| File exists on `main` AND the stash content has been functionally shipped under a different name / via another PR | `superseded` (drop, document the superseding PR in `phase1-classification.md`) |
| File exists on `main` AND the stash diff is largely a stale reversion of shipped work | `superseded` (drop, document which PRs the stash would revert) |
| File doesn't exist on `main` AND was deleted intentionally (i.e. the stash's deletion is a no-op) | `drop` (file deletion can't be applied — it's already gone) |
| File DOES exist on `main` AND the stash deletes it | `drop` (the deletion is a stale reversion of code retired since) |
| Concept in stash is valid but the diff is too stale to apply | `re-do` (open a new spec / task to write it fresh, document the seed) |

---

## DECIDE callouts

### D1 — Salvage strategy

**Status:** open

**Options:**
- (a) **Branch + cherry-pick path.** Restore the stash to a sacrificial branch off `main`, then per-file: `git checkout main -- <file>` for `superseded` / `drop` files, leaving only `keep` files. Commit those as a single salvage commit on a per-theme branch. Repeat per theme.
- (b) **Manual reconstruction path.** Don't apply the stash at all. Use `git stash show -p` as a reading reference and re-author each `keep` file fresh on a new branch.
- (c) **Hybrid.** (a) for pure-add files (no merge possible), (b) for modifications to existing files (current main has moved too far for a clean apply).

**Lean:** (c). Pure additions can be cherry-picked cleanly; modifications need re-authoring because of 39 commits of drift. Validate in Phase 0 design.

### D2 — Theme boundaries for PRs

**Status:** open

The 17 keep-candidate files (excluding the 2 pure deletions) span at least 4 themes. PR shape matters for review quality.

**Option (a) — 4 themed PRs:**

1. Voice / output refactor (`voice/formatter.py`, `workflows/output.py`, `tests/unit/voice/test_formatter.py`).
2. Release agents (`agents/release/release_models.py`, `release_prep_team.py`).
3. Ops dashboard supplement (`routes/dashboard.py`, `routes/runner.py`, `runner.py`, `static/css/*`, `static/js/*`, `templates/run_view.html`, `tests/unit/ops/test_runner.py`) — IF NOT SUPERSEDED by Phase 5.
4. CLI improvements (`cli_minimal.py`, `cli_commands/workflow_commands.py`).

**Option (b) — Combined "salvage" PR:** all keeps in one PR with a long body. Less reviewable, faster to land.

**Option (c) — Per-file PRs:** maximum review clarity, maximum overhead.

**Lean:** (a). 4 PRs is the right cardinality for this much heterogeneous work.

### D3 — Infra files (CLAUDE.md, settings.json, pre-commit)

**Status:** open

The infra additions are small (+88 lines total) and probably orthogonal to the feature work. Whether they go in their own PR or bundle with related themes:

**Lean:** own PR — these don't depend on the feature work and reviewing them under a "release agents" or "voice refactor" PR would bury them.

### D4 — Closeout

**Status:** open

After the salvage PRs land, how does this spec close?

**Options:**
- (a) Drop the stash with a closeout commit listing each file's disposition.
- (b) Preserve the stash with a note in this spec's `decisions.md` explaining why anything left wasn't worth salvaging.

**Lean:** (a) unless any file has unsalvageable-but-interesting content that's worth keeping around as a reading reference.

---

## Resolved decisions

(None yet — this is a draft.)
