---
name: plugin-read-skill-references-break-outside-the-plugin
source: .claude/CLAUDE.md
summary: This template explains why file path references in plugin commands fail when
  copied outside the plugin directory and how the `${CLAUDE_PLUGIN_ROOT}` variable
  resolution causes the breakage.
tags:
- claude-code
- packaging
type: faq
---

# FAQ: Why Do Plugin `Read Skill` References Break Outside the Plugin?

## Answer

The `file:///skills/doc-gen/SKILL.md` path in plugin commands is resolved relative to `${CLAUDE_PLUGIN_ROOT}`. When `attune setup` copies the command to `~/.claude/commands/`, this variable no longer points to the correct location, so the path fails to resolve.

**Problematic path:**

```
file:///skills/doc-gen/SKILL.md
```

## Related Topics

- **Error:** Plugin `Read skill` references break outside the plugin
