---
type: error
name: ruff-auto-fix-strips-imports-before-usage-code-exists
confidence: Verified
tags: [imports, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Ruff auto-fix strips imports before usage code exists

## Signature

Ruff auto-fix strips imports before usage code exists

## Root Cause

When adding `from mcp.server import Server` at the top of a file but the code using `Server(...)` is at the bottom (not yet written), ruff's `--fix` removes the import as unused. The edit succeeds but the import silently vanishes.

## Resolution

1. add imports and their usage code in the same edit, or add usage first then imports

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Ruff auto-fix strips imports before usage code exists
