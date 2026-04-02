---
type: faq
name: push-specific-tags-not-tags
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about push specific tags, not --tags?

## Answer

`git push origin main --tags` pushes ALL local tags, causing "already exists" rejections for old tags.

**How to fix:**
- Use `git push origin main v4.0.0` to push only the intended tag

```
git push origin main --tags
```

## Related Topics
- **Error**: Detailed error: Push specific tags, not `--tags`
