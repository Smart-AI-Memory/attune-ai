---
type: warning
name: dry-run-candidate-golden-queries-through-the-resolver-before
confidence: Verified
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Dry-run candidate golden queries through the
  resolver before assigning difficulty labels

## Condition

when expanding a golden-query fixture, every candidate query should pass through `resolve_topic()` (or the equivalent) first

## Risk

In the aggregator session, 2 of 12 candidates planned as `medium` actually lost to keyword collisions in other features' descriptions ("ai" → fix-test, "commands" → plugin) and had to be relabeled `hard`

## Mitigation

1. when expanding a golden-query fixture, every candidate query should pass through `resolve_topic()` (or the equivalent) first

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Dry-run candidate golden queries through the
  resolver before assigning difficulty labels
