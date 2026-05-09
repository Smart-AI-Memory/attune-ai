---
type: error
name: forced-cite-per-claim-prompting-is-the-structural-lever-for-rag
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: Forced cite-per-claim prompting is the structural
  lever for RAG faithfulness; soft grounding
  instructions cap much lower

## Signature

Forced cite-per-claim prompting is the structural
  lever for RAG faithfulness; soft grounding
  instructions cap much lower

## Root Cause

attune-rag v0.1.3 A/B sweep on the 15-query golden set. Baseline (no grounding rule): 46.7% hallucination rate. Strict variant ("answer ONLY from context, refuse otherwise"): 26.7% — a soft halving. Citation variant ([P1]/[P2] markers required per claim, no-cite = no claim): **6.7%** hallucination, 1.00 mean faithfulness. Mechanism: citation is *structurally enforceable* at generation time ("can I locate this claim in numbered passage N?"), whereas refusal instructions rely on the model policing its own drift. Cost: citations add ~5 tokens per claim and a small readability hit — generally worth it. Pattern generalizes beyond attune-rag: any RAG pipeline that needs faithfulness should default to a citation- forced prompt variant, not a "please use the context" one. Decision + data in `docs/rag/faithfulness-decision-2026-04-19.md`.

## Resolution

1. attune-rag v0.1.3 A/B sweep on the 15-query golden set

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Forced cite-per-claim prompting is the structural
  lever for RAG faithfulness; soft grounding
  instructions cap much lower
