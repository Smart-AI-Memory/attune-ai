# Cli

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

<!-- attune-generated: source_hash=bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4 feature=cli kind=reference generated_at=2026-06-24 -->
