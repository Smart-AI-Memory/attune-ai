---
type: faq
name: baseworkflow-uses-class-attributes-not-constructor-params
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `TypeError` (baseWorkflow uses class attributes, not constructor params)?

## Answer

The `name`, `description`, `stages`, and `tier_map` fields on BaseWorkflow are CLASS ATTRIBUTES, not `__init__()` parameters. Passing them to `super().__init__()` raises `TypeError`.

```
description
```

## Related Topics
- **Error**: Detailed error: BaseWorkflow uses class attributes, not constructor params
