---
type: troubleshooting
name: mcp-server-not-responding
tags: [mcp, claude-code, setup]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: MCP server not responding

## Symptom

Claude Code skills don't trigger or show 'MCP server unavailable'.

## Diagnosis

1. Check `.mcp.json` exists in the project root
2. Verify the command resolves: `which uv` or `which python`
3. Check if the MCP process is running: `ps aux | grep attune`
4. Test the server manually: `uv run python -m attune.mcp.server`

## Fix

Ensure `.mcp.json` uses `uv run` (not bare `python`) to resolve the correct venv. Restart Claude Code after fixing.

## Prevention

Use `uv run --from attune-ai` in .mcp.json to guarantee correct package resolution.

## Related Topics
- **Error**: Custom MCP stdio loop fails Claude Code handshake
- **Error**: .mcp.json python resolves to pyenv shim
