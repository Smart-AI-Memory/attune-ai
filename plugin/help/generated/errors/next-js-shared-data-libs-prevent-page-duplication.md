---
type: error
name: next-js-shared-data-libs-prevent-page-duplication
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Next.js shared data libs prevent page duplication

## Signature

Next.js shared data libs prevent page duplication

## Root Cause

When multiple pages need the same data array (e.g. wizard list), extract it to `lib/<name>.ts` and import from there. Defining the same array in `app/<page>/page.tsx` and a new `app/<page>/[param]/page.tsx` creates drift. The shared lib also enables `generateStaticParams()` and sitemap generation to stay in sync automatically.

## Resolution

1. When multiple pages need the same data array (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
