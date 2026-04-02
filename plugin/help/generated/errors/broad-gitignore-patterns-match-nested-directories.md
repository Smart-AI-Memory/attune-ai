---
type: error
name: broad-gitignore-patterns-match-nested-directories
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Broad gitignore patterns match nested directories

## Signature

Broad gitignore patterns match nested directories

## Root Cause

A root `.gitignore` entry `planning/` (without leading `/`) matches `plugin/skills/planning/` too. Scope patterns with `/planning/` for root-only, and add `!plugin/skills/planning/` exceptions when needed.

## Resolution

1. A root `.gitignore` entry `planning/` (without leading `/`) matches `plugin/skills/planning/` too

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
