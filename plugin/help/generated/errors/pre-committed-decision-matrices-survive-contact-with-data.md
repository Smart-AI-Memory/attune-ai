---
type: error
name: pre-committed-decision-matrices-survive-contact-with-data
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: Pre-committed decision matrices survive contact
  with data

## Signature

Pre-committed decision matrices survive contact
  with data

## Root Cause

the fastembed "if Golden P@1 ≥ 70%, defer" matrix was written into `docs/rag/embeddings-decision-2026-04-17.md` BEFORE running Phase 2.5c. When the data came in at 73.3%, there was zero temptation to move the goalpost — the matrix routed the decision cleanly. Pattern: for any gate-driven decision that could be contested after the fact ("we already invested X in this track, just ship it"), write the matrix before running the experiment and commit it to the repo. The commit timestamp is the arbiter, not your later preference.

## Resolution

1. the fastembed "if Golden P@1 ≥ 70%, defer" matrix was written into `docs/rag/embeddings-decision-2026-04-17.md` BEFORE running Phase 2.5c

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Pre-committed decision matrices survive contact
  with data
- Task: Update test mocks and assertions
