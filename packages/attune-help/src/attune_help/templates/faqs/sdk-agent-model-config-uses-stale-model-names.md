---
type: faq
name: sdk-agent-model-config-uses-stale-model-names
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle SDK agent MODEL_CONFIG uses stale model names?

## Answer

The `MODEL_CONFIG` dict in `agents/release/release_models.py` references `claude-3-5-haiku-latest` which returns 404. The current Haiku model ID is `claude-haiku-4-5-20251001`.

**How to fix:**
- Check model IDs against the Anthropic API when tier escalation fails at CHEAP

```
MODEL_CONFIG
```

## Related Topics
- **Error**: Detailed error: SDK agent MODEL_CONFIG uses stale model names
