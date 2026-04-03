---
type: error
name: duplicate-plugins-cause-conflicting-skill-triggers
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Error: Duplicate plugins cause conflicting skill triggers

## Signature

Duplicate plugins cause conflicting skill triggers

## Root Cause

Having both `attune-lite` and `attune-ai` installed creates duplicate skills (`security-audit`, `smart-test`, etc.). Claude sees both and must pick one, degrading UX. When consolidating plugins, deprecate the old one and uninstall it before installing the replacement.

## Resolution

1. Having both `attune-lite` and `attune-ai` installed creates duplicate skills (`security-audit`, `smart-test`, etc.)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
