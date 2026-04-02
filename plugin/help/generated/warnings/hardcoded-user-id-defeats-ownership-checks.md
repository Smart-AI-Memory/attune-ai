---
type: warning
name: hardcoded-user-id-defeats-ownership-checks
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Hardcoded `user_id` defeats ownership checks

## Condition

Adding ownership validation to memory handlers is pointless if the MCP server uses `user_id="mcp-session"` for everyone

## Risk

Ignoring this guidance may cause: Hardcoded `user_id` defeats ownership checks

## Mitigation

1. Adding ownership validation to memory handlers is pointless if the MCP server uses `user_id="mcp-session"` for everyone
2. Use `os.getlogin()` with fallback for non-interactive environments

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Hardcoded `user_id` defeats ownership checks
