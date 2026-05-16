---
type: tip
name: bug-predict-tip
feature: bug-predict
depth: tip
generated_at: 2026-05-16T06:19:45.795174+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0021e8cde
status: generated
---

# Tip: Scan before you merge, not after you ship

Run `/bug-predict` on a pull request branch before merging, not as a post-incident retrospective. The scanner surfaces `dangerous_eval`, broad exception swallowing, and incomplete code paths that code review routinely misses — finding them at merge time costs minutes; finding them in production costs hours.

## Why

Bug prediction's three subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — synthesize a unified report with file paths, line numbers, and an overall risk score. That output is most actionable when you still have room to act on it.

## Tradeoff

The risk score reflects pattern frequency and cyclomatic complexity, not runtime behavior. A file can score HIGH and never fail in practice if its broad exceptions carry `# INTENTIONAL:` markers or its `eval()` calls appear only in test fixtures. Treat HIGH findings as a prioritized review queue, not a definitive bug list.

## What to do next

After reviewing `/bug-predict` results, run `test-gen` to add coverage for flagged hotspots and `refactor-plan` to address the structural patterns driving the score.
