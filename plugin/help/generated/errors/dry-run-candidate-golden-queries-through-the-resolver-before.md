---
type: error
name: dry-run-candidate-golden-queries-through-the-resolver-before
confidence: Verified
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Dry-run candidate golden queries through the
  resolver before assigning difficulty labels

## Signature

Dry-run candidate golden queries through the
  resolver before assigning difficulty labels

## Root Cause

when expanding a golden-query fixture, every candidate query should pass through `resolve_topic()` (or the equivalent) first. Labels based on guessing — "this medium query probably resolves because the tag exists" — hide real corpus gaps and produce mislabeled fixtures. In the aggregator session, 2 of 12 candidates planned as `medium` actually lost to keyword collisions in other features' descriptions ("ai" → fix-test, "commands" → plugin) and had to be relabeled `hard`. The dry-run script is ~20 lines, takes under a second, and prevents every "unexpectedly hard medium query" false label. Pair with the existing lesson on "reclassify up the difficulty ladder instead of silencing" — this one prevents the silencing case by catching mislabels at authoring time.

## Resolution

1. when expanding a golden-query fixture, every candidate query should pass through `resolve_topic()` (or the equivalent) first

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Dry-run candidate golden queries through the
  resolver before assigning difficulty labels
- Task: Update test mocks and assertions
