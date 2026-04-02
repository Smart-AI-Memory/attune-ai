---
type: warning
name: stop-hooks-inject-stderr-not-stdout
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Stop hooks inject stderr, not stdout

## Condition

Claude Code's Stop hook with exit code 2 surfaces the hook's **stderr** as the feedback message

## Risk

Use `print(..., file=sys.stderr)` — `print()` writes to stdout which is silently discarded

## Mitigation

1. Use `print(..., file=sys.stderr)` — `print()` writes to stdout which is silently discarded

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Stop hooks inject stderr, not stdout
