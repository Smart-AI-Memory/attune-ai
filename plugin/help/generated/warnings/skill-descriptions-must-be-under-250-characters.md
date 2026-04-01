---
type: warning
name: skill-descriptions-must-be-under-250-characters
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Skill descriptions must be under 250 characters

## Condition

Anthropic truncates skill descriptions longer than 250 chars, which breaks auto-triggering from natural language

## Risk

Anthropic truncates skill descriptions longer than 250 chars, which breaks auto-triggering from natural language

## Mitigation

1. Always check with `len(description)` after editing SKILL.md frontmatter

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Skill descriptions must be under 250 characters
