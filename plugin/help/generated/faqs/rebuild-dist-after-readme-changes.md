---
type: faq
name: rebuild-dist-after-readme-changes
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about rebuild dist after README changes?

## Answer

PyPI uses `README.md` as the package description. If you update the README after the initial build, run `rm -rf dist/ && uv run python -m build` again before publishing or PyPI will show the old README.

```
rm -rf dist/ && uv run python -m build
```

## Related Topics
- **Error**: Detailed error: Rebuild dist after README changes
