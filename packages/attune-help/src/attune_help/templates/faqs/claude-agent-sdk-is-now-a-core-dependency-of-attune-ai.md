---
type: faq
name: claude-agent-sdk-is-now-a-core-dependency-of-attune-ai
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about claude-agent-sdk is now a core dependency of attune-ai?

## Answer

As of v4.2.0, the Agent SDK is included in core dependencies. No need for `pip install 'attune-ai[agent-sdk]'` — a plain `pip install attune-ai` includes it.

```
pip install 'attune-ai[agent-sdk]'
```

## Related Topics
- **Error**: Detailed error: `claude-agent-sdk` is now a core dependency of attune-ai
