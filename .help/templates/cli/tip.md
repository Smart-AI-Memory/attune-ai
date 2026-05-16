---
type: tip
name: cli-tip
feature: cli
depth: tip
generated_at: 2026-05-16T06:19:45.829217+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Tip: Use `HybridRouter.learn_preference()` to reduce repetitive routing

Teach the router your shorthand once, and it stops asking you to spell out the same skill invocations repeatedly.

**Why it sticks:** `HybridRouter` accumulates `usage_count` and `confidence` per keyword, so the more you reinforce a preference, the more reliably it fires.

Call `learn_preference(keyword, skill, args)` after any routing interaction you want to repeat. Then verify it with `get_suggestions(partial)` — if your keyword appears in the results, the router has it.

**Tradeoff:** Preferences are stored at `preferences_path`. If you share a config directory across projects, preferences learned in one context will surface as suggestions in another. Use a project-scoped path if that bleed-over would be confusing.

## Source files

- `src/attune/cli_router.py`
- `src/attune/cli_commands/`

**Tags:** `cli`, `commands`
