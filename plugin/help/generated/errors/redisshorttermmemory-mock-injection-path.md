---
type: error
name: redisshorttermmemory-mock-injection-path
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: RedisShortTermMemory mock injection path

## Signature

RedisShortTermMemory mock injection path

## Root Cause

After the facade refactor, `_client` is a read-only property on the facade. Tests must inject mocks via `memory._base._client = mock_client` (the plain attribute on `BaseOperations`), not `memory._client = MagicMock()`. Old tests using the direct path were all skipped with "Redis mocking API changed".

## Resolution

1. After the facade refactor, `_client` is a read-only property on the facade

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
