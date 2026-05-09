---
type: warning
name: exclude-hard-queries-from-aggregate-p-1-metrics-in-benchmark
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: Exclude `hard` queries from aggregate P@1
  metrics in benchmark caches

## Condition

when a golden- query fixture labels queries `easy/medium/hard` and `hard` documents structural ceilings (shared tags, genuine ambiguity), counting them in aggregate P@1 dilutes triage signal forever

## Risk

Hard queries still run via pytest xfail for ceiling tracking

## Mitigation

1. filter hard queries out of the cache writer's P@1 aggregation, keep them visible in drill-in views with their difficulty label, and record `p_at_1_excludes_hard: true` in the cache so consumers know the metric semantics

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Exclude `hard` queries from aggregate P@1
  metrics in benchmark caches
