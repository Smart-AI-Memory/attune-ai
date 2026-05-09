---
type: error
name: mcp-server-process-doesnt-inherit-env-variables
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP server process doesn't inherit `.env` variables

## Signature

MCP server process doesn't inherit `.env` variables

## Root Cause

The `${ANTHROPIC_API_KEY}` expansion in `.mcp.json` only works if the variable is already in the shell environment. If it's only in `.env`, the MCP server process won't have it.

## Resolution

1. call `load_dotenv()` in the server's `main()` entrypoint so features like the help polish pass can access the key at runtime

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
