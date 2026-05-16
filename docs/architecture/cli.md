# CLI architecture

Command-line interface and routing for attune.

## Purpose

The CLI layer owns two things: dispatching user-typed input to the correct command handler (cost tracking, help browsing, memory/lessons management), and learning per-user routing shortcuts via `HybridRouter` so that partial or keyword input resolves to a Claude Code skill invocation. It does **not** own rendering — that belongs to `transformers.py` — and it does not own the underlying data stores for costs, memory, or cross-links.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `RoutingPreference` | Dataclass that records one learned keyword→skill mapping with usage count and confidence score. | `src/attune/cli_router.py` |
| `HybridRouter` | Resolves free-form user input to a skill invocation by consulting stored `RoutingPreference` records; also updates those records via `learn_preference()` and surfaces completions via `get_suggestions()`. | `src/attune/cli_router.py` |

## Data flow

User input travels from the shell through the router, then fans out to one of four command groups:

```
User input (string)
        |
        v
  HybridRouter.route()
   |   consults: preferences file (RoutingPreference records)
   |
   +--[keyword match]--> skill invocation dict --> Claude Code
   |
   +--[cost commands]--> cmd_costs / cmd_costs_today
   |                     cmd_costs_export / cmd_costs_reset
   |
   +--[help commands]--> cmd_help
   |                       --> help_commands.py (browses templates)
   |
   +--[memory commands]--> cmd_remember / cmd_forget / cmd_lessons
                           cmd_memory_capture / cmd_memory_recall
```

`HybridRouter.learn_preference()` writes back to the preferences file after a successful routing decision, tightening future matches for the same keyword.

## Design decisions

**Learned routing lives in a separate dataclass, not in `HybridRouter` itself.** `RoutingPreference` is a plain dataclass so it can be serialized, inspected, and tested independently of the routing logic. Embedding confidence and usage count directly on the router would make those fields invisible to anything that needs to read or migrate the preferences file.

**Command groups are split across modules (`cost_commands.py`, `help_commands.py`, quick-memory module) rather than collected in one file.** Each group has a distinct `__all__` and can evolve independently. The tradeoff is that adding a new top-level command requires wiring it in two places (the module and the router), which is intentional — it keeps the router's dispatch table explicit.

## Extension points

- **Add a new command group:** Implement your command functions (signature `(args: Namespace) -> int`) in a new module, declare them in `__all__`, and register them as subcommands in the argument parser. The router's fan-out structure means you do not need to touch existing command modules.
- **Change how preferences are stored or scored:** Subclass or replace `RoutingPreference` — it is a plain dataclass with no base-class coupling. Pass a custom `preferences_path` to `HybridRouter.__init__()` to point at a different backing file.
- **Add a new routing strategy:** Extend `HybridRouter.route()`. The method receives the full `context` dict, so additional signals (project name, recent skill history) can influence resolution without changing the `RoutingPreference` schema.
- **Browse help from the CLI:** `cmd_help` delegates to `help_commands.py`. To add new template categories beyond `errors`, `warnings`, `tips`, and `references`, extend `_CATEGORIES` in that module and add the corresponding templates.

For rendering changes (Rich panels, markdown output), see `transformers.py` — that is outside this subsystem's scope.
