---
type: warning
name: duplicate-plugins-cause-conflicting-skill-triggers
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Duplicate plugins cause conflicting skill triggers

## Condition

Having both `attune-lite` and `attune-ai` installed creates duplicate skills (`security-audit`, `smart-test`, etc.)

## Risk

Ignoring this guidance may cause: Duplicate plugins cause conflicting skill triggers

## Mitigation

1. Having both `attune-lite` and `attune-ai` installed creates duplicate skills (`security-audit`, `smart-test`, etc.)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Duplicate plugins cause conflicting skill triggers
