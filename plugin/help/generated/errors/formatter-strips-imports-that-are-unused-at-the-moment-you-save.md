---
type: error
name: formatter-strips-imports-that-are-unused-at-the-moment-you-save
confidence: Verified
tags: [testing, imports, git, claude-code, packaging, python]
source: .claude/CLAUDE.md
---

# Error: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them

## Signature

Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them

## Root Cause

When staging multiple edits that together introduce a new import, the ruff/black autofix can run between edits and remove the import as unused. Happens reliably in the Claude Code hook pipeline. Two fixes: (1) introduce the import in the SAME edit that first uses it, not in a preceding edit; (2) scope the import inside the function body that uses it so the unused- import detector never fires even if the file is saved mid-edit. Scoping is more robust for tests.

## Resolution

1. When staging multiple edits that together introduce a new import, the ruff/black autofix can run between edits and remove the import as unused

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them
- Tip: Best practice: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them
- Task: Update test mocks and assertions
