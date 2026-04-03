---
type: error
name: push-specific-tags-not-tags
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Push specific tags, not `--tags`

## Signature

Push specific tags, not `--tags`

## Root Cause

`git push origin main --tags` pushes ALL local tags, causing "already exists" rejections for old tags. Use `git push origin main v4.0.0` to push only the intended tag.

## Resolution

1. Use `git push origin main v4.0.0` to push only the intended tag

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Push specific tags, not `--tags`
