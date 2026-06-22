---
type: tip
feature: code-quality
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Start with a quick scan before going deep

Run `/code-quality` with quick depth first to catch style issues and obvious problems before investing time in a thorough review.

The four-subagent workflow (security, quality, performance, architecture) takes several minutes on large codebases, but a quick scan finishes in seconds and catches 80% of the issues you'll actually fix. Deep reviews are valuable for critical modules, but most day-to-day development benefits more from fast feedback loops.

**Tradeoff:** Quick scans miss complex logic errors and architectural problems that only surface during deep analysis.
