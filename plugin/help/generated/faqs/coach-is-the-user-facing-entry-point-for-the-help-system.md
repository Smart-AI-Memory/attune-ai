---
type: faq
name: coach-is-the-user-facing-entry-point-for-the-help-system
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about /coach is the user-facing entry point for the .help system?

## Answer

The skill was renamed from `/help` to `/coach` because Claude Code's built-in `/help` command shadows plugin skills. `/coach` routes to the `.help` system via MCP tools (`help_lookup`, `help_init`, `help_status`, `help_update`, `help_maintain`).

```
 because Claude Code's built-in
```

## Related Topics
- **Error**: Detailed error: `/coach` is the user-facing entry point for the `.help`
  system
