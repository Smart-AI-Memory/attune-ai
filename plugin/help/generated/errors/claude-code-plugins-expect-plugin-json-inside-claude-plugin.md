---
type: error
name: claude-code-plugins-expect-plugin-json-inside-claude-plugin
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`

## Signature

Claude Code plugins expect `plugin.json` inside `.claude-plugin/`

## Root Cause

The correct location is `<plugin-root>/.claude-plugin/plugin.json`. Skills, commands, agents, and hooks directories go at the plugin root level alongside `.claude-plugin/`. Use `claude --plugin-dir ./plugin` to test local plugins during development.

## Resolution

1. Use `claude --plugin-dir ./plugin` to test local plugins during development

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Claude Code plugins expect `plugin.json` inside `.claude-plugin/`
- Task: Update test mocks and assertions
