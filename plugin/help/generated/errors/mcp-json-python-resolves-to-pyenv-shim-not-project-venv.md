---
type: error
name: mcp-json-python-resolves-to-pyenv-shim-not-project-venv
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: `.mcp.json` `python` resolves to pyenv shim, not project
  venv

## Signature

`.mcp.json` `python` resolves to pyenv shim, not project
  venv

## Root Cause

When Claude Code spawns an MCP server process via `"command": "python"`, the shell resolves to the pyenv shim which may have an ancient package version (e.g. v3.9.0 vs v5.4.0 in the venv).

## Resolution

1. use `"command": "uv", "args": ["run", "--from", "attune-ai", ...]` to ensure the correct package resolution

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `.mcp.json` `python` resolves to pyenv shim, not project
  venv
