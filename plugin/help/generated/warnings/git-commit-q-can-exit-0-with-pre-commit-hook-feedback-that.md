---
type: warning
name: git-commit-q-can-exit-0-with-pre-commit-hook-feedback-that
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `git commit -q` can exit 0 with pre-commit hook
  feedback that looks like success but isn't

## Condition

When pre-commit hooks (end-of-file-fixer, trailing- whitespace) modify files during the commit, the tail output shows "Passed" for each hook and gives no explicit "Aborted" line — but the commit is skipped and the files are left re-staged for retry

## Risk

Always verify with `git log --oneline -1` or `git status --short` immediately after `git commit`; don't trust that absence-of-error-message means the commit landed

## Mitigation

1. Always verify with `git log --oneline -1` or `git status --short` immediately after `git commit`; don't trust that absence-of-error-message means the commit landed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `git commit -q` can exit 0 with pre-commit hook
  feedback that looks like success but isn't
