---
type: error
name: exclude-hard-queries-from-aggregate-p-1-metrics-in-benchmark
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: Exclude `hard` queries from aggregate P@1
  metrics in benchmark caches

## Signature

Exclude `hard` queries from aggregate P@1
  metrics in benchmark caches

## Root Cause

when a golden- query fixture labels queries `easy/medium/hard` and `hard` documents structural ceilings (shared tags, genuine ambiguity), counting them in aggregate P@1 dilutes triage signal forever. A feature with a 3-query set (easy + medium + 1 hard miss) sits at 67% no matter what corpus fixes land, because the hard case is by design unsolvable without resolver changes.

## Resolution

1. filter hard queries out of the cache writer's P@1 aggregation, keep them visible in drill-in views with their difficulty label, and record `p_at_1_excludes_hard: true` in the cache so consumers know the metric semantics

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Exclude `hard` queries from aggregate P@1
  metrics in benchmark caches
- Task: Update test mocks and assertions
