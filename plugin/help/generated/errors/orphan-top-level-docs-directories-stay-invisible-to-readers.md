---
type: error
name: orphan-top-level-docs-directories-stay-invisible-to-readers
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav

## Signature

Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav

## Root Cause

`docs/rag/index.md` had existed since v6.1.0 but was never added to the mkdocs nav, so the rendered site had no path to it. Symptom: file is committed, `mkdocs build` processes it (it still renders HTML), but users browsing the site can't find it. Fix is trivial — add to `nav:` in `mkdocs.yml`. But the detection is hard: build succeeds without warning and the HTML file IS produced at the right URL. Two diagnostic commands: `grep -c "rag/index" mkdocs.yml` (returns 0 if orphan), and cross-check `find docs -name "index.md" -not -path "*archive*"` against nav entries. Whenever adding a new top-level directory under `docs/`, include nav wiring in the same PR.

## Resolution

1. `docs/rag/index.md` had existed since v6.1.0 but was never added to the mkdocs nav, so the rendered site had no path to it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav
- Tip: Best practice: Orphan top-level `docs/` directories stay
  invisible to readers until wired into `mkdocs.yml`
  nav
