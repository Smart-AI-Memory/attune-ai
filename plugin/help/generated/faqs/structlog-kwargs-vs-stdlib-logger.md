---
type: faq
name: structlog-kwargs-vs-stdlib-logger
tags: [imports]
source: CLAUDE.md Lessons Learned
---

# FAQ: What should I know about structlog kwargs vs stdlib Logger?

## Answer

`logger.info("msg", key=value)` is structlog syntax. stdlib `logging.Logger` raises `TypeError: info() got an unexpected keyword argument`.

**How to fix:**
- Use `logger.info("msg: key=%s", value)` instead

```
logger.info("msg", key=value)
```

## Related Topics
- **Error**: Detailed error: structlog kwargs vs stdlib Logger
