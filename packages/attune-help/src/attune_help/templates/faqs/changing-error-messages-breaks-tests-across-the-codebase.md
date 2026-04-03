---
type: faq
name: changing-error-messages-breaks-tests-across-the-codebase
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does changing error messages breaks tests across the codebase?

## Answer

Updating `_validate_file_path()`'s error from `"path must be within"` to `"outside allowed directory"` broke 10 test files. Before changing any error message in a shared function, grep the entire test suite for `match="<old message>"` and update all callers in the same commit.

```
_validate_file_path()
```

## Related Topics
- **Error**: Detailed error: Changing error messages breaks tests across the codebase
