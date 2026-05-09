---
type: warning
name: tags-pushed-before-squash-merge-point-to-the-wrong-commit
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Tags pushed before squash-merge point to the wrong commit

## Condition

If you push a tag before the PR merges (e.g., `git push origin v5.8.0`), the tag points to the pre-squash commit on the feature branch

## Risk

GitHub tag protection may block the force-push — see the existing lesson on protected tags

## Mitigation

1. If you push a tag before the PR merges (e.g., `git push origin v5.8.0`), the tag points to the pre-squash commit on the feature branch

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Tags pushed before squash-merge point to the wrong commit
