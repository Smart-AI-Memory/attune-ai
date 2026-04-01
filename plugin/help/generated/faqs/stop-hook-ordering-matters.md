---
type: faq
name: stop-hook-ordering-matters
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about stop hook ordering matters?

## Answer

When multiple Stop hook groups are configured, run state-saving hooks (exit 0) first and blocking hooks (exit 2) last. A trailing exit-0 hook may override a preceding exit-2 block.

## Related Topics
- **Error**: Detailed error: Stop hook ordering matters
