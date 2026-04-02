---
type: error
name: skill-descriptions-must-be-under-250-characters
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Skill descriptions must be under 250 characters

## Signature

Skill descriptions must be under 250 characters

## Root Cause

Anthropic truncates skill descriptions longer than 250 chars, which breaks auto-triggering from natural language. Always check with `len(description)` after editing SKILL.md frontmatter. Our initial migration had 7 of 11 skills over the limit.

## Resolution

1. Always check with `len(description)` after editing SKILL.md frontmatter

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Skill descriptions must be under 250 characters
