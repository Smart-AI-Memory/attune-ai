---
type: warning
name: pre-commit-black-unstaged-files-re-stage-after-failure
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Pre-commit black + unstaged files: re-stage after failure

## Condition

When `git commit` fails because black reformatted staged files, the reformatted files are in the working tree but unstaged

## Risk

When `git commit` fails because black reformatted staged files, the reformatted files are in the working tree but unstaged

## Mitigation

1. Run `git add <files>` again before retrying the commit

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-commit black + unstaged files: re-stage after failure
