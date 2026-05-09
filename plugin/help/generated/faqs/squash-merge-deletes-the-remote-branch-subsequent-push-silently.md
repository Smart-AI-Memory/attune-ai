---
type: faq
name: squash-merge-deletes-the-remote-branch-subsequent-push-silently
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about squash-merge deletes the remote branch; subsequent push silently recreates it with no PR attached?

## Answer

After a squash merge, GitHub deletes the feature branch. If you push more commits to the same branch name later, `git push` succeeds with `* [new branch]` output — GitHub recreates the branch but there's no PR attached.

**How to fix:**
- Always check `gh pr view <n> --json state` before adding more commits to a branch — if state is `MERGED`, rebase onto `origin/main` and open a new PR instead of pushing to the stale branch

```
 succeeds with
```

## Related Topics
- **Error**: Detailed error: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached
