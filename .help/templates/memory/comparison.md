---
type: comparison
name: memory-comparison
feature: memory
depth: comparison
generated_at: 2026-07-14T15:58:54.095241+00:00
source_hash: cba94c001e0b9e2f41279e9caa28b69cdc1ff0b0c62ec76baa038dc0e48cb5b6
status: generated
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

## Comparison

Memory's two tiers serve different retention horizons:

| Tier | API | Lifetime | Backed by |
|------|-----|----------|-----------|
| Short-term | `stash` / `retrieve` | TTL-expiring (seconds–days) | Redis or in-process |
| Long-term | `persist_pattern` / `recall_pattern` / `search_patterns` | Durable | Persistent storage |
| Staging | `stage_pattern` / `promote_pattern` | Until promoted or expired | Short-term, then long-term |
| Static | `ClaudeMemoryLoader.load_all_memory()` | Read-only project files | `CLAUDE.md` files |

Reach for **short-term** working memory for transient state, **staging
+ promotion** when a pattern should be reviewed before it becomes
durable, and **long-term patterns** for knowledge you'll search later.
`UnifiedMemory` exposes all three; `ClaudeMemoryLoader` is the separate
static-context path.
