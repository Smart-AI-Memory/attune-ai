---
type: tip
name: cli-tip
feature: cli
depth: tip
generated_at: 2026-06-04T23:39:47.662711+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Tip: working effectively with cli

Use `HybridRouter.learn_preference()` to teach the router your shortcuts — it's the fastest way to make the CLI feel native to your workflow.

**Why it sticks:** every preference you record increments `usage_count` and raises `confidence` on the matching `RoutingPreference`, so the router surfaces your patterns first instead of falling back to defaults.

**Tradeoff:** learned preferences are stored in a file (configured via `preferences_path` in `HybridRouter.__init__`). If you share a project across machines without syncing that file, each environment starts from scratch.

## How to apply this

1. Spot a command sequence you run often — for example, checking today's spend with `cmd_costs_today`.
2. Call `HybridRouter.learn_preference(keyword, skill, args='')` to record the mapping. The `keyword` field is what you type; `skill` is what gets invoked.
3. Use `HybridRouter.get_suggestions(partial)` while typing to confirm the router recognises your shorthand.
4. If a preference becomes stale, remove it rather than letting a low-`confidence` entry linger and produce unexpected routing results.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
