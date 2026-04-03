---
type: warning
name: exploration-agents-fabricate-names-verify-against-source
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: Exploration agents fabricate names — verify against
  source

## Condition

When generating docs, the Explore agent fabricated 10 of 14 agent template names (e.g

## Risk

"bug_predictor" instead of actual "test_coverage_analyzer")

## Mitigation

1. Always `grep` source files for IDs, class names, and counts before trusting agent-generated inventories

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Exploration agents fabricate names — verify against
  source
