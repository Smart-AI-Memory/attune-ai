---
type: error
name: after-a-squash-merge-of-a-feature-branch-local-main-can-have
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash

## Signature

After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash

## Root Cause

If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash. Safe fix: run `git log --oneline main ^origin/main` to see the "extra" local commits, confirm the content is included in the squash (`git show <squash-commit> --stat` shows the expected files), then `git reset --hard origin/main`.

## Resolution

1. If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash
