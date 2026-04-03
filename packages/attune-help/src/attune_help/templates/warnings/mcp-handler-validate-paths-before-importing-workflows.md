---
type: warning
name: mcp-handler-validate-paths-before-importing-workflows
confidence: Verified
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: MCP handler: validate paths before importing workflows

## Condition

In `server.py`, `_validate_file_path()` must run before the lazy `from attune.workflows.X import XWorkflow` import

## Risk

If the import fails (wrong class name, missing dep), the path validation never fires and the security check is bypassed

## Mitigation

1. Always: validate first, import second

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: MCP handler: validate paths before importing workflows
