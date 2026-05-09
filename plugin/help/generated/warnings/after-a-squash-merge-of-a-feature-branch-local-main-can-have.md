---
type: warning
name: after-a-squash-merge-of-a-feature-branch-local-main-can-have
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash

## Condition

If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash

## Risk

If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash

## Mitigation

1. If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash
