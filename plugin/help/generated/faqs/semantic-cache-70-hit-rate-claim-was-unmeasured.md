---
type: faq
name: semantic-cache-70-hit-rate-claim-was-unmeasured
source: .claude/CLAUDE.md
---

# FAQ: What should I know about semantic cache 70% hit rate claim was unmeasured?

## Answer

Telemetry data (`~/.attune/telemetry/usage.jsonl`, 17,264 requests) showed 0.2% hit rate and $0.26 saved out of $72. The 0.95 similarity threshold and non-repetitive workflow prompts (unique file paths, timestamps, code snippets) meant near-matches almost never fired.

**How to fix:**
- Always verify performance claims against actual telemetry before documenting them

```
~/.attune/telemetry/usage.jsonl
```

## Related Topics
- **Error**: Detailed error: Semantic cache 70% hit rate claim was unmeasured
