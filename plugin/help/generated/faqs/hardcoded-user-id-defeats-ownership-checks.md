---
type: faq
name: hardcoded-user-id-defeats-ownership-checks
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about hardcoded user_id defeats ownership checks?

## Answer

Adding ownership validation to memory handlers is pointless if the MCP server uses `user_id="mcp-session"` for everyone. Fix the identity layer (Fix 5) before or alongside the authorization layer (Fix 4).

**How to fix:**
- Use `os.getlogin()` with fallback for non-interactive environments

```
user_id="mcp-session"
```

## Related Topics
- **Error**: Detailed error: Hardcoded `user_id` defeats ownership checks
