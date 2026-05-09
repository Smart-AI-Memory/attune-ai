---
type: faq
name: mcp-server-process-doesnt-inherit-env-variables
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why MCP server process doesn't inherit .env variables?

## Answer

The `${ANTHROPIC_API_KEY}` expansion in `.mcp.json` only works if the variable is already in the shell environment. If it's only in `.env`, the MCP server process won't have it.

**How to fix:**
- call `load_dotenv()` in the server's `main()` entrypoint so features like the help polish pass can access the key at runtime

```
${ANTHROPIC_API_KEY}
```

## Related Topics
- **Error**: Detailed error: MCP server process doesn't inherit `.env` variables
