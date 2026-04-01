---
type: faq
name: github-protected-tags-cannot-be-force-updated
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: Why gitHub protected tags cannot be force-updated?

## Answer

Once a tag is pushed, `git push --force` fails if repository rules protect tags. Tag the correct commit before pushing — there's no easy fix after.

```
git push --force
```

## Related Topics
- **Error**: Detailed error: GitHub protected tags cannot be force-updated
