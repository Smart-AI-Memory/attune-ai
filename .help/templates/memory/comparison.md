---
type: comparison
name: memory-comparison
feature: memory
depth: comparison
generated_at: 2026-06-23T21:52:16.487778+00:00
source_hash: 544951b28662066a703ef7be552af08e83ef52a5186e5ad71ad216119352938b
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
