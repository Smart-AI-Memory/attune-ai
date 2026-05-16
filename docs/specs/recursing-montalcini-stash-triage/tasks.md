# Tasks — Recursing-Montalcini Stash Triage

**Status:** draft (2026-05-16)

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Stash extraction + per-file classification | not started | Read-only; produces `phase1-classification.md` |
| Phase 1 — Theme split + branch plan | gated on Phase 0 | Decision matrix applied |
| Phase 2 — Salvage PRs (one per theme) | gated on Phase 1 | 1 working session per theme cap |
| Phase 3 — Closeout + stash drop | gated on Phase 2 | |

---

## Phase 0 — Classification (~1 hour, read-only)

**Goal:** apply the per-file matrix from `decisions.md` to all 19 files. No code changes.

- [ ] **0.1** Extract the full stash diff to `phase0-data/stash-3-full.diff` for reference. (Already saved at `/tmp/stash-3-recursing-montalcini.diff`; copy into the spec dir so it survives `/tmp` cleanup.)
- [ ] **0.2** Per-file matrix application. For each of the 19 files:
  - Does the file exist on `origin/main`? (`git ls-tree origin/main -- <path>`)
  - If yes, what's the diff content shape? (refactor / addition / reversion)
  - If no, is the stash adding it as net-new? (look for `new file mode` in the stash hunk header)
  - Apply the matrix → write classification + 1-sentence rationale.
- [ ] **0.3** Cross-check ops/* files against PR #413's Phase 5 infra. The dashboard / runner / static changes may overlap with shipped work.
- [ ] **0.4** Cross-check workflows/output.py refactor against any output-cleanup PRs since 2026-04-14 (the stash branch's likely creation date).
- [ ] **0.5** Cross-check `release_models.py` against current `agents/release/` contents — if a similarly-named file exists, the stash may be a renamed/refactored version.
- [ ] **0.6** Write `phase0-data/phase1-classification.md` with the per-file table and rationales. Output the salvage-vs-drop split by file count and by line count.

**Output gate**: `phase1-classification.md` exists and every file has a classification. If the salvage line-count is < 200 (i.e., barely worth the effort), apply `decisions.md` D4 lean and skip directly to Phase 3 (drop stash with rationale).

**Budget cap**: 1 hour of reading. No LLM cost.

---

## Phase 1 — Theme split + branch plan (~30 min)

- [ ] **1.1** Resolve `decisions.md` D1 (salvage strategy), D2 (theme boundaries), D3 (infra files) based on Phase 0 findings.
- [ ] **1.2** Write `phase1-branch-plan.md` listing each planned PR: branch name, files included, theme summary, rebase strategy.
- [ ] **1.3** Sanity-check: total salvage line count divided by per-PR line count, sanity-checked against the 1-session-per-theme cap.

---

## Phase 2 — Salvage PRs (one session per theme, ≤4 sessions)

Per the D1 hybrid lean: pure-add files cherry-picked, modifications re-authored.

For each theme branch:

- [ ] **2.x.1** Create branch off `origin/main`.
- [ ] **2.x.2** For pure-add files: extract from stash via `git show 'stash@{3}^{tree}':<path> > <path>`. Verify content + format.
- [ ] **2.x.3** For modification files: read the stash diff as reference, re-author the change against current `main`.
- [ ] **2.x.4** Run tests for the theme. CI green BEFORE opening PR.
- [ ] **2.x.5** Open PR with body that explicitly notes this is salvage work from `recursing-montalcini` stash, links to this spec, and lists per-file changes.
- [ ] **2.x.6** After merge, mark the theme as ✓ in this file.

Anticipated themes (subject to Phase 0 classification):

- [ ] **2.A** Voice / output refactor.
- [ ] **2.B** Release agents.
- [ ] **2.C** Ops dashboard supplement (skip if superseded by Phase 5).
- [ ] **2.D** CLI improvements.
- [ ] **2.E** Infra (CLAUDE.md, settings.json, pre-commit).

---

## Phase 3 — Closeout (~10 min)

- [ ] **3.1** Verify all themes from Phase 2 are either merged or explicitly skipped with rationale in `phase1-classification.md`.
- [ ] **3.2** Drop the stash (`git stash drop 'stash@{N}'` — find current N via `git stash list`; index may have drifted again).
- [ ] **3.3** Add closeout note to `decisions.md` listing each salvaged-vs-dropped file with the merged PR number or drop rationale.
- [ ] **3.4** Mark spec complete; move to `_sequencing.md` Done section.

---

## Retirement criteria

This spec auto-retires if any of the following:

- Phase 0 classification finds < 200 lines of salvageable work — too little to justify the per-theme PR overhead. Drop the stash with a rationale commit, skip to Phase 3.
- 60 days pass without Phase 0 being started — the stash content drifts further from `main` every day; past 60 days, almost everything will need to be re-done rather than salvaged, and re-doing is "new feature work," which doesn't need this spec.
- A different session ships work that supersedes ≥80% of the stash content. Document the supersession in `decisions.md` D4 and drop the stash.

Retirement note in `decisions.md` with one-line summary.
