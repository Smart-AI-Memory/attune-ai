---
type: warning
name: claude-code-plugins-expect-plugin-json-inside-claude-plugin
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`

## Condition

The correct location is `<plugin-root>/.claude-plugin/plugin.json`

## Risk

Ignoring this guidance may cause: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`

## Mitigation

1. Use `claude --plugin-dir ./plugin` to test local plugins during development

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`
