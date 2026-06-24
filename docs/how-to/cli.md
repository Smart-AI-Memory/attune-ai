# Cli

## Quickstart

Check the install and list commands:

```bash
attune --help
attune doctor
```

Run an analysis workflow:

```bash
attune workflow run security-audit
```

## Tasks

### Run a workflow from the CLI

```bash
attune workflow list                 # what's available
attune workflow run code-review      # run one
attune workflow info code-review     # describe it
```

**Verify:** `attune workflow run <slug>` executes the named workflow;
`attune workflow list` enumerates the registered workflows.

### View usage and cost

```bash
attune telemetry show
attune telemetry savings
attune costs today
```

**Verify:** these read the local telemetry store (the same one the
`telemetry` feature writes).

### Route natural-language input in Python

```python
import asyncio

from attune.cli_router import is_slash_command, route_user_input

print(is_slash_command("/security"))          # True
print(is_slash_command("scan my code"))        # False

result = asyncio.run(route_user_input("run a security audit"))
print(result["workflow"], result["confidence"])
```

**Verify:** `is_slash_command` is synchronous; `route_user_input` is
**async** — await it (here via `asyncio.run`). The result dict includes
`workflow`, `skill`, `confidence`, `reasoning`, and `args`.

### List routable workflows

```python
from attune.cli_router import SmartRouter

router = SmartRouter()
print(router.list_workflows())                 # synchronous
```

**Verify:** `SmartRouter.list_workflows()` is synchronous; `route` is
async and `route_sync` is its synchronous counterpart.

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

<!-- attune-generated: source_hash=bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4 feature=cli kind=how-to generated_at=2026-06-24 -->
