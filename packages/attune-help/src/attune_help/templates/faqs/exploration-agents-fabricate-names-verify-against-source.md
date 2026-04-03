---
type: faq
name: exploration-agents-fabricate-names-verify-against-source
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about exploration agents fabricate names — verify against source?

## Answer

When generating docs, the Explore agent fabricated 10 of 14 agent template names (e.g. "bug_predictor" instead of actual "test_coverage_analyzer").

**How to fix:**
- Always `grep` source files for IDs, class names, and counts before trusting agent-generated inventories

## Related Topics
- **Error**: Detailed error: Exploration agents fabricate names — verify against
  source
