---
type: warning
name: formatter-strips-imports-that-are-unused-at-the-moment-you-save
confidence: Verified
tags: [testing, imports, git, claude-code, packaging, python]
source: .claude/CLAUDE.md
---

# Warning: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them

## Condition

When staging multiple edits that together introduce a new import, the ruff/black autofix can run between edits and remove the import as unused

## Risk

Ignoring this guidance may cause: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them

## Mitigation

1. When staging multiple edits that together introduce a new import, the ruff/black autofix can run between edits and remove the import as unused

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them
