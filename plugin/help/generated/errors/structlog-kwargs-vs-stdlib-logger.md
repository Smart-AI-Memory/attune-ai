---
type: error
name: structlog-kwargs-vs-stdlib-logger
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Error: structlog kwargs vs stdlib Logger

## Signature

TypeError: info() got an unexpected keyword argument

## Root Cause

`logger.info("msg", key=value)` is structlog syntax. stdlib `logging.Logger` raises `TypeError: info() got an unexpected keyword argument`. Use `logger.info("msg: key=%s", value)` instead. When fixing, grep the entire module — partial fixes leave runtime crashes in untouched calls.

## Resolution

1. Use `logger.info("msg: key=%s", value)` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: structlog kwargs vs stdlib Logger
