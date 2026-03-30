---
type: faq
name: pureposixpath-strips-trailing-slashes
tags: [testing, security]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: `PurePosixPath` strips trailing slashes?

## Answer

The test fixture `_passthrough` returns `PurePosixPath(path)`, which strips trailing slashes (`"src/"` → `"src"`). Tests asserting exact path strings passed through `_validate_file_path` must account for this.


**Fix:**

- Use `in ("src/", "src")` or check `call_args.kwargs` instead of `assert_awaited_once_with`

```
_passthrough
```

## Related Topics
- **Error**: Detailed error: `PurePosixPath` strips trailing slashes
