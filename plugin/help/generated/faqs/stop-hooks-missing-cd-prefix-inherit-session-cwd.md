---
type: faq
name: stop-hooks-missing-cd-prefix-inherit-session-cwd
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why stop hooks missing cd prefix inherit session cwd?

## Answer

Stop hooks without an explicit `cd /abs/path &&` prefix inherit whatever directory Claude Code was started from — which may not be the repo root.

**How to fix:**
- Always prefix Stop (and all) hook commands with `cd /Users/patrickroebuck/attune-ai &&` to guarantee the correct working directory regardless of where the session was opened

```
cd /abs/path &&
```

## Related Topics
- **Error**: Detailed error: Stop hooks missing `cd` prefix inherit session cwd
