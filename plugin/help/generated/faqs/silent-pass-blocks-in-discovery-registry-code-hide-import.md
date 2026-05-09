---
type: faq
name: silent-pass-blocks-in-discovery-registry-code-hide-import
tags: [imports]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ImportError` (silent pass blocks in discovery/registry code hide import failures)?

## Answer

Workflow discovery had 6 silent `pass` blocks that swallowed `ImportError`/`AttributeError`. When a workflow disappeared from `attune workflow list`, there was no diagnostic output at any log level.

**How to fix:**
- Always use `logger.warning()` in discovery paths so `--verbose` or log inspection can surface the root cause

```
 blocks that swallowed
```

## Related Topics
- **Error**: Detailed error: Silent `pass` blocks in discovery/registry code hide
  import failures
