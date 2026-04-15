---
type: note
feature: cli
depth: note
generated_at: 2026-04-14T15:12:37.820329+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# Note: cli

## Context

The Attune CLI provides a hybrid interface that combines traditional command-line parsing with natural language routing to AI skills.

## Content

The CLI architecture separates core functionality into two main components:

**Routing System** (`HybridRouter` and `RoutingPreference`): The router interprets user input and directs it to appropriate skill invocations. It maintains learned preferences to improve routing accuracy over time. The `RoutingPreference` dataclass tracks user patterns with keywords, target skills, arguments, usage counts, and confidence scores.

**Command Interface** (`main()`, `create_parser()`, and command handlers): Traditional CLI commands handle specific operations like cost tracking (`cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset`) and help browsing (`cmd_help`). The parser recognizes both explicit commands and natural language input for hybrid operation.

**Integration Points**: The `route_user_input()` function provides the bridge between parsed input and skill execution. Slash commands receive special handling through `is_slash_command()` detection.

Cost tracking commands operate on usage data with export capabilities and reset functionality. Help commands browse documentation templates across predefined categories: errors, warnings, tips, and references.

## Source files

- `src/attune/cli_minimal.py` — Core CLI entry point and argument parsing
- `src/attune/cli_router.py` — Hybrid routing and preference learning
- `src/attune/cli_commands/` — Individual command implementations

**Tags:** `cli`, `commands`
