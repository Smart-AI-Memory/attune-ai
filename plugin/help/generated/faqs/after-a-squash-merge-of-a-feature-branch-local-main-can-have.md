---
type: faq
name: after-a-squash-merge-of-a-feature-branch-local-main-can-have
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about after a squash merge of a feature branch, local main can have "extra" commits that are already in the squash?

## Answer

If you had any of the feature branch commits locally on main before the squash (e.g., from a pull on release/v5.10.0 that got replayed onto main), `git pull` after the squash merge tries to rebase and conflicts because the same tree content exists on main at a different commit hash. Safe fix: run `git log --oneline main ^origin/main` to see the "extra" local commits, confirm the content is included in the squash (`git show <squash-commit> --stat` shows the expected files), then `git reset --hard origin/main`.

```
git log --oneline main ^origin/main
```

## Related Topics
- **Error**: Detailed error: After a squash merge of a feature branch, local main can
  have "extra" commits that are already in the squash
