---
name: mcp-server-not-responding
source: CLAUDE.md Lessons Learned
summary: This troubleshooting guide helps developers diagnose and resolve issues where
  MCP servers fail to respond in Claude Code, covering symptom identification, diagnostic
  checks, configuration fixes using `uv run`, and prevention strategies.
tags:
- mcp
- claude-code
- setup
type: troubleshooting
---

# Troubleshooting: MCP Server Not Responding

## Symptom

Claude Code skills fail to trigger, or the interface displays an **MCP server unavailable** error.

## Diagnosis

Work through the following checks in order:

1. Confirm `.mcp.json` exists in the project root.
2. Verify the required command is resolvable on your `PATH`:
   ```bash
   which uv
   # or
   which python
   ```
3. Check whether the MCP process is currently running:
   ```bash
   ps aux | grep attune
   ```
4. Start the server manually to surface any startup errors:
   ```bash
   uv run python -m attune.mcp.server
   ```

## Fix

Ensure `.mcp.json` invokes `uv run` rather than a bare `python` call. Using `uv run` guarantees the command executes inside the correct virtual environment and resolves the right dependencies.

After updating `.mcp.json`, **restart Claude Code** for the changes to take effect.

## Prevention

Use the following invocation in `.mcp.json` to ensure reliable package resolution regardless of the active Python environment:

```bash
uv run --from attune-ai
```

## Related Topics

- [Error: Custom MCP stdio loop fails Claude Code handshake](#)
- [Error: `.mcp.json` python resolves to pyenv shim](#)
