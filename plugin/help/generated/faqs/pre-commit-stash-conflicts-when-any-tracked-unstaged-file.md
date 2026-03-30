---
type: faq
name: pre-commit-stash-conflicts-when-any-tracked-unstaged-file
tags: [testing, git, claude-code, python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files?

## Answer

Even a single unrelated unstaged tracked file (e.g. `memdocs_storage/test_key.json`) triggers pre-commit's stash/restore cycle.


**Fix:**

- `git stash push` the unstaged tracked files before committing, then `git stash pop` after

```
memdocs_storage/test_key.json
```

## Related Topics
- **Error**: Detailed error: Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files
