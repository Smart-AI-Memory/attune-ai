---
type: faq
name: claude-code-plugins-expect-plugin-json-inside-claude-plugin
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about claude Code plugins expect plugin.json inside .claude-plugin/?

## Answer

The correct location is `<plugin-root>/.claude-plugin/plugin.json`. Skills, commands, agents, and hooks directories go at the plugin root level alongside `.claude-plugin/`.

**How to fix:**
- Use `claude --plugin-dir ./plugin` to test local plugins during development

```
<plugin-root>/.claude-plugin/plugin.json
```

## Related Topics
- **Error**: Detailed error: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`
