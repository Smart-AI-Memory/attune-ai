---
type: error
name: stop-hooks-inject-stderr-not-stdout
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Stop hooks inject stderr, not stdout

## Signature

Stop hooks inject stderr, not stdout

## Root Cause

Claude Code's Stop hook with exit code 2 surfaces the hook's **stderr** as the feedback message. Use `print(..., file=sys.stderr)` — `print()` writes to stdout which is silently discarded.

## Resolution

1. Use `print(..., file=sys.stderr)` — `print()` writes to stdout which is silently discarded

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Stop hooks inject stderr, not stdout
