---
type: warning
name: mkdocs-build-crashing-with-attributeerror-nonetype-object-has
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: `mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug

## Condition

hit during PR #175 (docs freshness pass)

## Risk

Before wasting time investigating local doc changes, check with `git stash && mkdocs build` on the pre-change tree — if it still crashes, you've ruled out the current PR

## Mitigation

1. Before wasting time investigating local doc changes, check with `git stash && mkdocs build` on the pre-change tree — if it still crashes, you've ruled out the current PR

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug
