---
type: warning
name: pureposixpath-strips-trailing-slashes
confidence: Verified
tags: [testing, security]
source: .claude/CLAUDE.md
---

# Warning: `PurePosixPath` strips trailing slashes

## Condition

The test fixture `_passthrough` returns `PurePosixPath(path)`, which strips trailing slashes (`"src/"` → `"src"`)

## Risk

Ignoring this guidance may cause: `PurePosixPath` strips trailing slashes

## Mitigation

1. Use `in ("src/", "src")` or check `call_args.kwargs` instead of `assert_awaited_once_with`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `PurePosixPath` strips trailing slashes
