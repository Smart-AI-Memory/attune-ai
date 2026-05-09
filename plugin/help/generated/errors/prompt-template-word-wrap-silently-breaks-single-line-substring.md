---
type: error
name: prompt-template-word-wrap-silently-breaks-single-line-substring
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Prompt-template word wrap silently breaks single-line
  substring assertions in tests

## Signature

 in out` but fails `

## Root Cause

a template with a sentence like "The provided context does not\ncover this question." passes `"The provided context" in out` but fails `"context does not cover" in out` because the phrase straddles a newline.

## Resolution

1. normalize whitespace at the assertion boundary with `" ".join(out.split())`, or pick a substring that cannot wrap

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Prompt-template word wrap silently breaks single-line
  substring assertions in tests
- Task: Update test mocks and assertions
