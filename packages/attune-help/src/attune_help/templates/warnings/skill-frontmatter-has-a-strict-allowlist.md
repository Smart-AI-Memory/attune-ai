---
type: warning
name: skill-frontmatter-has-a-strict-allowlist
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Skill frontmatter has a strict allowlist

## Condition

Claude Code skills only support these YAML frontmatter fields: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `compatibility`, `license`, `metadata`

## Risk

Ignoring this guidance may cause: Skill frontmatter has a strict allowlist

## Mitigation

1. Claude Code skills only support these YAML frontmatter fields: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `compatibility`, `license`, `metadata`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Skill frontmatter has a strict allowlist
