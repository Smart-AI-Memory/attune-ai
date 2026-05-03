---
name: ghost-command-references-survive-cli-renames
source: .claude/CLAUDE.md
summary: This template explains how stale command references can persist silently
  across a codebase after a CLI rename and provides strategies for catching and preventing
  them through grep searches and automated validation tests.
tags:
- testing
type: faq
---

# FAQ: How do ghost command references survive CLI renames?

## Answer

Renaming `empathy` → `attune` left 30+ stale command references scattered across discovery tips, workflow output, template definitions, and docstrings in 15 files. These ghost references compile and run without errors, making them easy to miss until a user encounters broken instructions.

After any CLI rename, take the following steps:

1. **Grep the entire `src/` directory** for the old command name to catch all stale references:
   ```bash
   grep -r "empathy" src/
   ```
2. **Add a validation test** that compares every user-facing command string against the actual registered CLI subcommands, so future renames break the test suite immediately rather than silently shipping broken docs.

## Related Topics

- **Error**: Ghost command references survive CLI renames
