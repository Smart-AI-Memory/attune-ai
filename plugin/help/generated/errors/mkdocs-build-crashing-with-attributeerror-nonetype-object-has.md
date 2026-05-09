---
type: error
name: mkdocs-build-crashing-with-attributeerror-nonetype-object-has
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug

## Signature

`mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug

## Root Cause

hit during PR #175 (docs freshness pass). Reproduces on clean `main` without any of the PR's changes — confirmed via `git stash` then build. Trace ends at `self.filename = html.escape(self._decodeifneeded(options.get('filename', '')))` where `options.get('filename', '')` returns `None` instead of the empty-string default (because some caller explicitly passed `filename=None` for a code fence). Before wasting time investigating local doc changes, check with `git stash && mkdocs build` on the pre-change tree — if it still crashes, you've ruled out the current PR. Fix direction (not done this session): pin compatible `pygments` / `pymdown-extensions` versions in the docs extra, or find the specific markdown file whose fence triggers the None filename.

## Resolution

1. hit during PR #175 (docs freshness pass)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `mkdocs build` crashing with
  `AttributeError: 'NoneType' object has no
  attribute 'replace'` in
  `pymdownx/highlight.py:400 → pygments/formatters/html.py:434`
  is a pygments / pymdown-extensions version mismatch,
  not a content bug
