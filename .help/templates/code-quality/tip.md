---
type: tip
feature: code-quality
depth: tip
generated_at: 2026-04-19T18:47:03.313407+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Start with a quick scan before going deep

Run `/code-quality` with quick depth first to catch style issues and obvious problems before investing time in a thorough review.

The four-subagent workflow (security, quality, performance, architecture) takes several minutes on large codebases, but a quick scan finishes in seconds and catches 80% of the issues you'll actually fix. Deep reviews are valuable for critical modules, but most day-to-day development benefits more from fast feedback loops.

**Tradeoff:** Quick scans miss complex logic errors and architectural problems that only surface during deep analysis.
