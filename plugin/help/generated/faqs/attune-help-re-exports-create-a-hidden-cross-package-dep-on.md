---
type: faq
name: attune-help-re-exports-create-a-hidden-cross-package-dep-on
tags: [imports, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about attune.help re-exports create a hidden cross-package dep on attune-author?

## Answer

`src/attune/help/__init__.py` does `from attune_author.generator import ...` at module level. This works in dev because `[tool.uv.sources]` resolves `attune-author` from the local workspace path, but a vanilla `pip install attune-ai` from PyPI will fail at import time unless `attune-author` is also published.

```
src/attune/help/__init__.py
```

## Related Topics
- **Error**: Detailed error: `attune.help` re-exports create a hidden cross-package
  dep on `attune-author`
