---
type: warning
name: mcp-json-python-resolves-to-pyenv-shim-not-project-venv
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: `.mcp.json` `python` resolves to pyenv shim, not project
  venv

## Condition

When Claude Code spawns an MCP server process via `"command": "python"`, the shell resolves to the pyenv shim which may have an ancient package version (e.g

## Risk

Ignoring this guidance may cause: `.mcp.json` `python` resolves to pyenv shim, not project
  venv

## Mitigation

1. use `"command": "uv", "args": ["run", "--from", "attune-ai", ...]` to ensure the correct package resolution

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `.mcp.json` `python` resolves to pyenv shim, not project
  venv
