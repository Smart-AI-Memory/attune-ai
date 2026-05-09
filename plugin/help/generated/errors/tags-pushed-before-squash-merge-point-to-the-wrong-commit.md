---
type: error
name: tags-pushed-before-squash-merge-point-to-the-wrong-commit
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Tags pushed before squash-merge point to the wrong commit

## Signature

Tags pushed before squash-merge point to the wrong commit

## Root Cause

If you push a tag before the PR merges (e.g., `git push origin v5.8.0`), the tag points to the pre-squash commit on the feature branch. After squash-merge, the main branch has a different commit hash. You must delete the old tag and re-tag the merge commit: `git tag -d v5.8.0 && git tag -a v5.8.0 -m "..." && git push origin v5.8.0 --force`. GitHub tag protection may block the force-push — see the existing lesson on protected tags.

## Resolution

1. If you push a tag before the PR merges (e.g., `git push origin v5.8.0`), the tag points to the pre-squash commit on the feature branch

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
