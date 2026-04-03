---
type: faq
name: mcp-json-python-resolves-to-pyenv-shim-not-project-venv
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about .mcp.json python resolves to pyenv shim, not project venv?

## Answer

When Claude Code spawns an MCP server process via `"command": "python"`, the shell resolves to the pyenv shim which may have an ancient package version (e.g. v3.9.0 vs v5.4.0 in the venv).

**How to fix:**
- use `"command": "uv", "args": ["run", "--from", "attune-ai", ...]` to ensure the correct package resolution

```
"command": "python"
```

## Related Topics
- **Error**: Detailed error: `.mcp.json` `python` resolves to pyenv shim, not project
  venv
