---
type: error
name: pre-commit-black-unstaged-files-re-stage-after-failure
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Pre-commit black + unstaged files: re-stage after failure

## Signature

Pre-commit black + unstaged files: re-stage after failure

## Root Cause

When `git commit` fails because black reformatted staged files, the reformatted files are in the working tree but unstaged. Run `git add <files>` again before retrying the commit. This is distinct from the stash conflict issue — here the hook succeeds at formatting but the commit is rejected because files changed.

## Resolution

1. Run `git add <files>` again before retrying the commit

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Pre-commit black + unstaged files: re-stage after failure
