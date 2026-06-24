---
name: cli
source: content/features/cli.md
tags:
- cli
- commands
type: reference
---

# The attune command-line interface and its natural-language router

## Reference

### Invocation

| Surface | Invocation |
|---------|------------|
| Console script | `attune <command>` (`attune.cli_minimal:main`). |
| Module | `python -m attune.cli_minimal`. |
| Help / health | `attune --help`, `attune doctor`. |

### `attune.cli_router`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `is_slash_command(text) -> bool` | fn (sync) | Is this a `/command`? |
| `route_user_input(user_input, context=None) -> dict` | fn (**async**) | Route text → workflow/skill dict. |
| `SmartRouter` | class | `route` (async) / `route_sync` / `list_workflows` / `get_workflow_info` / `suggest_for_error` / `suggest_for_file`. |
| `HybridRouter` | class | `route`, `get_suggestions`, `learn_preference`. |
| `RoutingPreference` | dataclass | Routing preferences. |
