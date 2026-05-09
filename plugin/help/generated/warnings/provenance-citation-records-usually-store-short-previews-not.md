---
type: warning
name: provenance-citation-records-usually-store-short-previews-not
confidence: Verified
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# Warning: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it

## Condition

`attune_rag.provenance.CitedSource.excerpt` caps at 200 chars

## Risk

Fix: add a `context: str` field on the pipeline result dataclass (`RagResult.context` in this case) so downstream consumers get the *exact* passage block the generator saw

## Mitigation

1. add a `context: str` field on the pipeline result dataclass (`RagResult.context` in this case) so downstream consumers get the *exact* passage block the generator saw

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it
