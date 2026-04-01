---
type: faq
name: redisshorttermmemory-mock-injection-path
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about redisShortTermMemory mock injection path?

## Answer

After the facade refactor, `_client` is a read-only property on the facade. Tests must inject mocks via `memory._base._client = mock_client` (the plain attribute on `BaseOperations`), not `memory._client = MagicMock()`.

```
 is a read-only property on the facade. Tests must inject mocks via
```

## Related Topics
- **Error**: Detailed error: RedisShortTermMemory mock injection path
