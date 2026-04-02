---
type: warning
name: structlog-kwargs-vs-stdlib-logger
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Warning: structlog kwargs vs stdlib Logger

## Condition

`logger.info("msg", key=value)` is structlog syntax

## Risk

stdlib `logging.Logger` raises `TypeError: info() got an unexpected keyword argument`

## Mitigation

1. Use `logger.info("msg: key=%s", value)` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: structlog kwargs vs stdlib Logger
