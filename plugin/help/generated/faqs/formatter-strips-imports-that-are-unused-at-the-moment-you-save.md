---
type: faq
name: formatter-strips-imports-that-are-unused-at-the-moment-you-save
tags: [testing, imports, git, claude-code, packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about formatter strips imports that are "unused" at the moment you save, even if a later edit will use them?

## Answer

When staging multiple edits that together introduce a new import, the ruff/black autofix can run between edits and remove the import as unused. Happens reliably in the Claude Code hook pipeline.

## Related Topics
- **Error**: Detailed error: Formatter strips imports that are "unused" at the
  moment you save, even if a later edit will use them
