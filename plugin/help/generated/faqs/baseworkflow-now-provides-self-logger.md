---
type: faq
name: baseworkflow-now-provides-self-logger
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about baseWorkflow now provides self.logger?

## Answer

Fixed in `c67ad740`. `BaseWorkflow.__init__` sets `self.logger = logging.getLogger(type(self).__module__)` so all subclasses get an instance logger namespaced to their own module.

```
BaseWorkflow.__init__
```

## Related Topics
- **Error**: Detailed error: BaseWorkflow now provides `self.logger`
