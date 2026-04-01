---
type: faq
name: gitignore-exclusions-break-ci-tests-that-read-those-files
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: Why does .gitignore exclusions break CI tests that read those files?

## Answer

If tests call `read_spec(".claude/plans/foo.md")` but `.gitignore` excludes `.claude/plans/`, CI will never have the file. Either track the files or skip the tests when absent.

```
read_spec(".claude/plans/foo.md")
```

## Related Topics
- **Error**: Detailed error: `.gitignore` exclusions break CI tests that read those
  files
