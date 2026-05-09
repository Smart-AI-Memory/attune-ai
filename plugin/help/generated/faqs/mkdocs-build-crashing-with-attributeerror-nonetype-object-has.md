---
type: faq
name: mkdocs-build-crashing-with-attributeerror-nonetype-object-has
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: Why does mkdocs build crashing with AttributeError: 'NoneType' object has no attribute 'replace' in pymdownx/highlight.py:400 → pygments/formatters/html.py:434 is a pygments / pymdown-extensions version mismatch, not a content bug?

## Answer

hit during PR #175 (docs freshness pass). Reproduces on clean `main` without any of the PR's changes — confirmed via `git stash` then build.

```
 without any of the PR's changes — confirmed via
```

## Related Topics
- **Error**: Detailed error: `mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug
