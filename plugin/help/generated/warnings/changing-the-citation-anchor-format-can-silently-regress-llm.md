---
type: warning
name: changing-the-citation-anchor-format-can-silently-regress-llm
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Changing the citation-anchor format can silently
  regress LLM citation fidelity even when the
  instructions are "equivalent"

## Condition

initial attune-rag 0.1.5 implementation replaced `[P1] source: <path>` headers with an XML `id="P1"` attribute on a `<passage>` sentinel tag, and updated the prompt instruction from "citation marker pointing at the passages" to "pointing at the `id` attribute of the passage(s)"

## Risk

Ignoring this guidance may cause: Changing the citation-anchor format can silently
  regress LLM citation fidelity even when the
  instructions are "equivalent"

## Mitigation

1. initial attune-rag 0.1.5 implementation replaced `[P1] source: <path>` headers with an XML `id="P1"` attribute on a `<passage>` sentinel tag, and updated the prompt instruction from "citation marker pointing at the passages" to "pointing at the `id` attribute of the passage(s)"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Changing the citation-anchor format can silently
  regress LLM citation fidelity even when the
  instructions are "equivalent"
