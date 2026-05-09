---
type: warning
name: orphan-top-level-docs-directories-stay-invisible-to-readers
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav

## Condition

`docs/rag/index.md` had existed since v6.1.0 but was never added to the mkdocs nav, so the rendered site had no path to it

## Risk

Ignoring this guidance may cause: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav

## Mitigation

1. `docs/rag/index.md` had existed since v6.1.0 but was never added to the mkdocs nav, so the rendered site had no path to it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav
