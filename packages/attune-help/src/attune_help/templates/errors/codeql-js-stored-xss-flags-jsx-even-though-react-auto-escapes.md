---
type: error
name: codeql-js-stored-xss-flags-jsx-even-though-react-auto-escapes
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: CodeQL `js/stored-xss` flags JSX even though React auto-escapes

## Signature

CodeQL `js/stored-xss` flags JSX even though React auto-escapes

## Root Cause

CodeQL flagged `{tag}` rendered in `<h1>` as stored XSS despite React's automatic text escaping. Defense-in-depth fix: `decodeURIComponent` on input + `encodeURIComponent` on `href` values. `generateStaticParams` constrains valid values but CodeQL can't see that.

## Resolution

1. CodeQL flagged `{tag}` rendered in `<h1>` as stored XSS despite React's automatic text escaping

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
