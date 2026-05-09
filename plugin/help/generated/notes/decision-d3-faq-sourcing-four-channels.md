---
type: note
name: decision-d3-faq-sourcing-four-channels
tags: [architecture, design-decision]
source: .claude/plans/documentation-stack-spec.md
---

# Note: Design decision: FAQ sourcing (four channels)

## Context

Documentation stack architecture decision.

## Content

FAQs are sourced from:

1. **Unmatched user queries** — questions that don't
   match existing templates become FAQ candidates
2. **Repeated error patterns** — errors that appear
   frequently in telemetry get promoted to FAQ
3. **GitHub issues** — questions from issues/
   discussions feed the FAQ pipeline
4. **Author-curated** — the developer can associate
   FAQ entries with features manually when shipping
   new functionality

All four channels feed into FAQ templates. The engine
deduplicates and ranks by frequency.

## Related Topics

_No related topics yet._
