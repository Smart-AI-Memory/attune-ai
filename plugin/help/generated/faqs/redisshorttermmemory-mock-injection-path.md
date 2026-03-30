---
type: faq
name: redisshorttermmemory-mock-injection-path
tags: [testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: RedisShortTermMemory mock injection path?

## Answer

After the facade refactor, `_client` is a read-only property on the facade. Tests must inject mocks via `memory._base._client = mock_client` (the plain attribute on `BaseOperations`), not `memory._client = MagicMock()`.

```
 is a read-only property on the facade. Tests must inject mocks via
```

## Related Topics
- **Error**: Detailed error: RedisShortTermMemory mock injection path
