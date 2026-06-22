---
type: tip
name: hooks-tip
feature: hooks
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 92f76c4d4d77b21e59b9a6aed8e65dd221371f5ce10f2941171a5c0310c232c1
status: generated
---

# Tip: working effectively with hooks

Use `HookRegistry.get_execution_log()` to understand what your hooks are actually doing before you debug anything else.

**Why:** Hook failures are usually silent — the registry ran, nothing crashed, but the handler never fired. The execution log tells you which hooks matched, which were skipped by their `HookMatcher`, and what each `execute()` call returned. Guessing without it wastes time.

**How:** Call `registry.get_execution_log(limit=20, event_filter=your_event)` immediately after a `fire()` or `fire_sync()` call. If a handler you expected to run is missing from the log, check whether its `HookMatcher.matches()` returned `False` for your context dict — that is the most common reason a registered hook silently does nothing.

**Tradeoff:** The log is capped at 100 entries by default and is not persisted across sessions. For long-running processes, call `get_stats()` periodically and `clear_execution_log()` after each inspection to avoid stale entries obscuring recent activity.

**Tags:** `hooks`, `webhooks`, `events`, `automation`
