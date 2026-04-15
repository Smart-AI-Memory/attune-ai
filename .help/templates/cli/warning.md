---
type: warning
feature: cli
depth: warning
generated_at: 2026-04-14T15:11:40.212231+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI cautions

## What to watch for

The Attune CLI combines traditional argument parsing with natural language routing, creating opportunities for unexpected behavior when commands don't resolve as expected.

## Risk areas

### Routing ambiguity in natural language input

The `HybridRouter` learns user preferences over time, which can cause the same input to route differently across sessions or users. A command that worked yesterday might invoke a different skill today if the router's confidence threshold shifts.

**Mitigation:** Use explicit slash commands (`/skill-name`) when you need predictable routing, especially in scripts or automation.

### Cost tracking data persistence

Cost tracking commands (`cmd_costs_*`) maintain state between CLI invocations. The `cmd_costs_reset()` function irreversibly clears all historical data with no confirmation prompt.

**Mitigation:** Export cost data (`attune costs export`) before running reset operations, particularly in shared environments where other users depend on the tracking history.

### Context leakage between router calls

The `route_user_input()` function accepts a context dictionary that persists learned preferences. Reusing context objects across unrelated routing calls can pollute the preference learning with incorrect associations.

**Mitigation:** Create fresh context dictionaries for independent routing operations, or explicitly clear context between unrelated command sequences.

### Argument parsing edge cases with natural language

The CLI parser expects traditional flags and arguments, but users may input natural language that resembles valid arguments. This can cause the parser to misinterpret intent when routing falls back to conventional parsing.

**Mitigation:** Validate user input with `is_slash_command()` before attempting argument parsing. Handle parsing exceptions gracefully when dealing with ambiguous input.

## How to avoid problems

1. **Test routing behavior explicitly.** The hybrid router's machine learning aspect means identical code can behave differently based on learned preferences. Test both fresh router instances and routers with various preference states.

2. **Handle routing failures gracefully.** Natural language routing can fail in ways traditional CLI parsing cannot. Always check the routing result and provide fallback behavior for unrecognized input.

3. **Isolate cost tracking in tests.** Use temporary preferences paths when testing router functionality to avoid polluting persistent cost data or learned preferences.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
