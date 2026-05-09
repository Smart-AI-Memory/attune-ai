---
type: faq
name: gh-pr-merge-admin-prints-a-fast-forward-warning-even-when-the
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about gh pr merge --admin prints a fast-forward warning even when the remote merge succeeds?

## Answer

After an admin-merge, the CLI attempts a local fast-forward of your local main to origin/main. If your local main diverged (e.g., you had feature-branch commits before the squash), the CLI prints `fatal: Not possible to fast-forward, aborting` and `! warning: not possible to fast-forward to: "main"`.

**How to fix:**
- Always verify the actual merge state via `gh pr view <n> --json state,mergedAt,mergeCommit` before assuming the command failed

```
fatal: Not possible to fast-forward, aborting
```

## Related Topics
- **Error**: Detailed error: `gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds
