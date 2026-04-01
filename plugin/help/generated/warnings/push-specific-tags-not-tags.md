---
type: warning
name: push-specific-tags-not-tags
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Push specific tags, not `--tags`

## Condition

`git push origin main --tags` pushes ALL local tags, causing "already exists" rejections for old tags

## Risk

`git push origin main --tags` pushes ALL local tags, causing "already exists" rejections for old tags

## Mitigation

1. Use `git push origin main v4.0.0` to push only the intended tag

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Push specific tags, not `--tags`
