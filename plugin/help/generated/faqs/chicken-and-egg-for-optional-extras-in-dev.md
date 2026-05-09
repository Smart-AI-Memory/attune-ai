---
type: faq
name: chicken-and-egg-for-optional-extras-in-dev
tags: [ci, testing, imports, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about chicken-and-egg for optional extras in [dev]?

## Answer

If you want `pkg>=X,<Y` in `[dev]` extra so CI tests actually exercise the code paths (rather than `pytest.importorskip` and skip silently), the package MUST be resolvable — i.e., on PyPI, or the workspace source exists in the CI checkout. Publishing the package is the unblocker when you're working in the monorepo-sibling pattern where CI doesn't have the sibling checkout.

```
 extra so CI tests actually exercise the code paths (rather than
```

## Related Topics
- **Error**: Detailed error: Chicken-and-egg for optional extras in [dev]
