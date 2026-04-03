---
type: warning
name: plugin-read-skill-references-break-outside-the-plugin
confidence: Verified
tags: [claude-code, packaging]
source: .claude/CLAUDE.md
---

# Warning: Plugin `Read skill` references break outside the plugin

## Condition

The `file:///skills/doc-gen/SKILL.md` path in plugin commands is relative to `${CLAUDE_PLUGIN_ROOT}`

## Risk

Ignoring this guidance may cause: Plugin `Read skill` references break outside the plugin

## Mitigation

1. The `file:///skills/doc-gen/SKILL.md` path in plugin commands is relative to `${CLAUDE_PLUGIN_ROOT}`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Plugin `Read skill` references break outside the plugin
