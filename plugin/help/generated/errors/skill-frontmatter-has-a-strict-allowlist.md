---
type: error
name: skill-frontmatter-has-a-strict-allowlist
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Skill frontmatter has a strict allowlist

## Signature

Skill frontmatter has a strict allowlist

## Root Cause

Claude Code skills only support these YAML frontmatter fields: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `compatibility`, `license`, `metadata`. Fields like `allowed-tools`, `model`, `context`, `agent`, and `hooks` are NOT valid for skills (they may apply to agents or commands). The IDE linter catches these — always check diagnostics after editing SKILL.md frontmatter.

## Resolution

1. Claude Code skills only support these YAML frontmatter fields: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `compatibility`, `license`, `metadata`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Skill frontmatter has a strict allowlist
