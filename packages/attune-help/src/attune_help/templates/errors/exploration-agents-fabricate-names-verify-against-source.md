---
type: error
name: exploration-agents-fabricate-names-verify-against-source
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Exploration agents fabricate names — verify against
  source

## Signature

Exploration agents fabricate names — verify against
  source

## Root Cause

When generating docs, the Explore agent fabricated 10 of 14 agent template names (e.g. "bug_predictor" instead of actual "test_coverage_analyzer"). Always `grep` source files for IDs, class names, and counts before trusting agent-generated inventories. This applies to any generated content that enumerates codebase entities.

## Resolution

1. Always `grep` source files for IDs, class names, and counts before trusting agent-generated inventories

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Exploration agents fabricate names — verify against
  source
- Task: Update test mocks and assertions
