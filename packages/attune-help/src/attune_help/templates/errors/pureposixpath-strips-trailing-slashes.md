---
type: error
name: pureposixpath-strips-trailing-slashes
confidence: Verified
tags: [testing, security]
source: .claude/CLAUDE.md
---

# Error: `PurePosixPath` strips trailing slashes

## Signature

`PurePosixPath` strips trailing slashes

## Root Cause

The test fixture `_passthrough` returns `PurePosixPath(path)`, which strips trailing slashes (`"src/"` → `"src"`). Tests asserting exact path strings passed through `_validate_file_path` must account for this. Use `in ("src/", "src")` or check `call_args.kwargs` instead of `assert_awaited_once_with`.

## Resolution

1. Use `in ("src/", "src")` or check `call_args.kwargs` instead of `assert_awaited_once_with`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `PurePosixPath` strips trailing slashes
- Task: Update test mocks and assertions
