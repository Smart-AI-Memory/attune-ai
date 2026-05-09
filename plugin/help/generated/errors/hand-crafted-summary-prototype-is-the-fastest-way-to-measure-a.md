---
type: error
name: hand-crafted-summary-prototype-is-the-fastest-way-to-measure-a
confidence: Verified
tags: [testing, security, git, packaging]
source: .claude/CLAUDE.md
---

# Error: Hand-crafted summary prototype is the fastest way
  to measure a RAG ceiling before committing to an
  LLM polish pipeline

## Signature

Hand-crafted summary prototype is the fastest way
  to measure a RAG ceiling before committing to an
  LLM polish pipeline

## Root Cause

Before building the 0.7.0 polish pipeline (hours of work + LLM budget), I hand-crafted keyword-rich path-keyed summaries for nine bug-predict templates in ~15 min, pointed a scratch `DirectoryCorpus` at them, and reran the fixture benchmark. The +40 pt P@1 result validated the entire spec's thesis empirically. Pattern: for any corpus-level improvement that will be automated later, hand-craft one feature first and measure. The hand-crafted result is the ceiling the automation must approach. If hand-crafting underperforms expectations, don't build the automation at all.

## Resolution

1. Before building the 0.7.0 polish pipeline (hours of work + LLM budget), I hand-crafted keyword-rich path-keyed summaries for nine bug-predict templates in ~15 min, pointed a scratch `DirectoryCorpus` at them, and reran the fixture benchmark

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Hand-crafted summary prototype is the fastest way
  to measure a RAG ceiling before committing to an
  LLM polish pipeline
- Task: Update test mocks and assertions
