---
type: error
name: skill-frontmatter-allowlist-march-2026
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Skill frontmatter allowlist (March 2026)

## Signature

Skill frontmatter allowlist (March 2026)

## Root Cause

Valid fields are `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`. Fields `compatibility`, `license`, and `metadata` are NOT in the official docs and should not be used. The old lesson about a strict 8-field allowlist was outdated.

## Resolution

1. Valid fields are `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Skill frontmatter allowlist (March 2026)
