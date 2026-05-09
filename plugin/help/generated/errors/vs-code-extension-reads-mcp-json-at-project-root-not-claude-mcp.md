---
type: error
name: vs-code-extension-reads-mcp-json-at-project-root-not-claude-mcp
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: VS Code extension reads `.mcp.json` at project root, not
  `.claude/mcp.json`

## Signature

VS Code extension reads `.mcp.json` at project root, not
  `.claude/mcp.json`

## Root Cause

The Claude Code CLI reads `.claude/mcp.json` but the VS Code extension reads `.mcp.json` at the project root. To support both, maintain both files with identical content. A committed `.claude/mcp.json` alone won't start local MCP servers in VS Code.

## Resolution

1. The Claude Code CLI reads `.claude/mcp.json` but the VS Code extension reads `.mcp.json` at the project root

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
