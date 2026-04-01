---
type: error
name: mcp-handler-validate-paths-before-importing-workflows
confidence: Verified
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP handler: validate paths before importing workflows

## Signature

MCP handler: validate paths before importing workflows

## Root Cause

In `server.py`, `_validate_file_path()` must run before the lazy `from attune.workflows.X import XWorkflow` import. If the import fails (wrong class name, missing dep), the path validation never fires and the security check is bypassed. Always: validate first, import second.

## Resolution

1. Always: validate first, import second

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: MCP handler: validate paths before importing workflows
- Tip: Best practice: MCP handler: validate paths before importing workflows
