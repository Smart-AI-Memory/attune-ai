---
type: faq
name: mkdocs-strict-treats-broken-links-as-fatal-errors
tags: [ci]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: mkdocs `--strict` treats broken links as fatal errors?

## Answer

The CI docs build uses `mkdocs build --strict` even though `mkdocs.yml` has `strict: false`. When source files are deleted but docs still link to them, the CI build fails with "Aborted with N warnings in strict mode!" Move stale docs to `docs/archive/` (excluded by mkdocs `exclude_docs` config) rather than fixing every dead link.

```
mkdocs build --strict
```

## Related Topics
- **Error**: Detailed error: mkdocs `--strict` treats broken links as fatal errors
