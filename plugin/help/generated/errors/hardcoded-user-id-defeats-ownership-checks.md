---
type: error
name: hardcoded-user-id-defeats-ownership-checks
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Hardcoded `user_id` defeats ownership checks

## Signature

Hardcoded `user_id` defeats ownership checks

## Root Cause

Adding ownership validation to memory handlers is pointless if the MCP server uses `user_id="mcp-session"` for everyone. Fix the identity layer (Fix 5) before or alongside the authorization layer (Fix 4). Use `os.getlogin()` with fallback for non-interactive environments.

## Resolution

1. Adding ownership validation to memory handlers is pointless if the MCP server uses `user_id="mcp-session"` for everyone
2. Use `os.getlogin()` with fallback for non-interactive environments

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Hardcoded `user_id` defeats ownership checks
