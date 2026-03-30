---
type: faq
name: exploration-agents-fabricate-names-verify-against-source
tags: [testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Exploration agents fabricate names — verify against
  source?

## Answer

When generating docs, the Explore agent fabricated 10 of 14 agent template names (e.g. "bug_predictor" instead of actual "test_coverage_analyzer").


**Fix:**

- Always `grep` source files for IDs, class names, and counts before trusting agent-generated inventories

## Related Topics
- **Error**: Detailed error: Exploration agents fabricate names — verify against
  source
