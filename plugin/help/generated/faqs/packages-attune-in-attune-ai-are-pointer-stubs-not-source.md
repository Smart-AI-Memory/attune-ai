---
type: faq
name: packages-attune-in-attune-ai-are-pointer-stubs-not-source
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about packages/attune-*/ in attune-ai are pointer stubs, not source?

## Answer

`packages/attune-author/` and `packages/attune-help/` contain a single README.md that points at the real sibling repo (`/Users/patrickroebuck/attune-{author,help}/`). The actual package source, `pyproject.toml`, tests, and CI live in those sibling directories.

```
packages/attune-author/
```

## Related Topics
- **Error**: Detailed error: `packages/attune-*/` in attune-ai are pointer stubs, not
  source
