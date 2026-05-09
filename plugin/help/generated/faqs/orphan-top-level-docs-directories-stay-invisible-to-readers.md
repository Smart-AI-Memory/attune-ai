---
type: faq
name: orphan-top-level-docs-directories-stay-invisible-to-readers
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about orphan top-level docs/ directories stay invisible to readers until wired into mkdocs.yml nav?

## Answer

`docs/rag/index.md` had existed since v6.1.0 but was never added to the mkdocs nav, so the rendered site had no path to it. Symptom: file is committed, `mkdocs build` processes it (it still renders HTML), but users browsing the site can't find it.

```
docs/rag/index.md
```

## Related Topics
- **Error**: Detailed error: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav
