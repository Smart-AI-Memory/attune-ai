---
type: faq
name: ghost-command-references-survive-cli-renames
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about ghost command references survive CLI renames?

## Answer

Renaming `empathy` → `attune` left 30+ stale command references in discovery tips, workflow output, template definitions, and docstrings across 15 files. After any CLI rename, grep the entire `src/` for the old name and add a validation test that checks user-facing command strings against the actual registered CLI subcommands.

## Related Topics
- **Error**: Detailed error: Ghost command references survive CLI renames
