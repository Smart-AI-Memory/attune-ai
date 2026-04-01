---
type: warning
name: redisshorttermmemory-mock-injection-path
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: RedisShortTermMemory mock injection path

## Condition

After the facade refactor, `_client` is a read-only property on the facade

## Risk

Ignoring this guidance may cause: RedisShortTermMemory mock injection path

## Mitigation

1. After the facade refactor, `_client` is a read-only property on the facade

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: RedisShortTermMemory mock injection path
