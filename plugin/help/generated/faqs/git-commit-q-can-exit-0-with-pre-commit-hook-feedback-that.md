---
type: faq
name: git-commit-q-can-exit-0-with-pre-commit-hook-feedback-that
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about git commit -q can exit 0 with pre-commit hook feedback that looks like success but isn't?

## Answer

When pre-commit hooks (end-of-file-fixer, trailing- whitespace) modify files during the commit, the tail output shows "Passed" for each hook and gives no explicit "Aborted" line — but the commit is skipped and the files are left re-staged for retry.

**How to fix:**
- Always verify with `git log --oneline -1` or `git status --short` immediately after `git commit`; don't trust that absence-of-error-message means the commit landed

```
git log --oneline -1
```

## Related Topics
- **Error**: Detailed error: `git commit -q` can exit 0 with pre-commit hook
  feedback that looks like success but isn't
