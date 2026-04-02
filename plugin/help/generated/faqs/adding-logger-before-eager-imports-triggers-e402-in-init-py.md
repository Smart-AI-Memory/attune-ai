---
type: faq
name: adding-logger-before-eager-imports-triggers-e402-in-init-py
tags: [imports, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about adding logger before eager imports triggers E402 in __init__.py?

## Answer

Placing `logger = logging.getLogger(__name__)` between stdlib imports and eager `from .module import ...` lines makes ruff flag all subsequent relative imports as E402 (module-level import not at top). Move the logger assignment after ALL imports, just before the first non-import statement.

```
logger = logging.getLogger(__name__)
```

## Related Topics
- **Error**: Detailed error: Adding `logger` before eager imports triggers E402 in
  `__init__.py`
