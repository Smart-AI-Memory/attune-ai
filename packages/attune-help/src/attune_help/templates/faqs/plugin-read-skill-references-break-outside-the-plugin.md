---
type: faq
name: plugin-read-skill-references-break-outside-the-plugin
tags: [claude-code, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why does plugin Read skill references break outside the plugin?

## Answer

The `file:///skills/doc-gen/SKILL.md` path in plugin commands is relative to `${CLAUDE_PLUGIN_ROOT}`. When the command is copied to `~/.claude/commands/` via `attune setup`, the path doesn't resolve.

```
file:///skills/doc-gen/SKILL.md
```

## Related Topics
- **Error**: Detailed error: Plugin `Read skill` references break outside the plugin
