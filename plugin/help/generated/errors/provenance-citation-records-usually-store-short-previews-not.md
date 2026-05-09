---
type: error
name: provenance-citation-records-usually-store-short-previews-not
confidence: Verified
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# Error: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it

## Signature

Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it

## Root Cause

`attune_rag.provenance.CitedSource.excerpt` caps at 200 chars. A faithfulness judge fed `.excerpt` would score answers against truncated passages and mis-flag supported claims as unsupported.

## Resolution

1. add a `context: str` field on the pipeline result dataclass (`RagResult.context` in this case) so downstream consumers get the *exact* passage block the generator saw

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it
- Tip: Best practice: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it
