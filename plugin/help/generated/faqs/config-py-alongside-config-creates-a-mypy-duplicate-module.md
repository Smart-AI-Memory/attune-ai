---
type: faq
name: config-py-alongside-config-creates-a-mypy-duplicate-module
tags: [imports, git, python]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle config.py alongside config/ creates a mypy duplicate module?

## Answer

Having both `src/attune/config.py` and `src/attune/config/__init__.py` causes mypy to report "Duplicate module named attune.config". This blocks mypy in pre-commit.

```
src/attune/config.py
```

## Related Topics
- **Error**: Detailed error: `config.py` alongside `config/` creates a mypy duplicate
  module
