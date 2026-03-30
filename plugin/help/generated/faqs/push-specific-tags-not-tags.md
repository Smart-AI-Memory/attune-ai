---
type: faq
name: push-specific-tags-not-tags
tags: [git]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Push specific tags, not `--tags`?

## Answer

`git push origin main --tags` pushes ALL local tags, causing "already exists" rejections for old tags.


**Fix:**

- Use `git push origin main v4.0.0` to push only the intended tag

```
git push origin main --tags
```

## Related Topics
- **Error**: Detailed error: Push specific tags, not `--tags`
