---
name: mcp-json-python-resolves-to-pyenv-shim-not-project-venv
source: .claude/CLAUDE.md
summary: This template explains how to resolve issues where the `python` command in
  `.mcp.json` configuration files incorrectly uses a pyenv shim instead of a project's
  virtualenv by using `uv run` instead.
tags:
- claude-code
type: faq
---

# FAQ: `.mcp.json` `python` Resolves to pyenv Shim Instead of Project Virtualenv

## Problem

When Claude Code spawns an MCP server process using `"command": "python"`, the shell resolves `python` to the pyenv shim rather than the Python interpreter in your project's virtualenv. This can result in outdated package versions being used — for example, v3.9.0 from the shim instead of v5.4.0 installed in the venv.

## Solution

Use `uv run` to invoke the MCP server. This ensures the correct package and interpreter are resolved regardless of the active pyenv environment.

Replace:

```json
"command": "python"
```

With:

```json
"command": "uv",
"args": ["run", "--from", "attune-ai", "..."]
```

The `--from` flag tells `uv` to resolve the specified package and run the command using the correct environment, bypassing pyenv shim resolution entirely.

## Related Topics

- **Error reference:** `.mcp.json` — `python` resolves to pyenv shim, not project virtualenv
