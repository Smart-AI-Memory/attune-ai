---
type: error
name: mkdocs-strict-treats-broken-links-as-fatal-errors
confidence: Verified
tags: [ci]
source: .claude/CLAUDE.md
---

# Error: mkdocs `--strict` treats broken links as fatal errors

## Signature

mkdocs `--strict` treats broken links as fatal errors

## Root Cause

The CI docs build uses `mkdocs build --strict` even though `mkdocs.yml` has `strict: false`. When source files are deleted but docs still link to them, the CI build fails with "Aborted with N warnings in strict mode!" Move stale docs to `docs/archive/` (excluded by mkdocs `exclude_docs` config) rather than fixing every dead link.

## Resolution

1. The CI docs build uses `mkdocs build --strict` even though `mkdocs.yml` has `strict: false`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: mkdocs `--strict` treats broken links as fatal errors
