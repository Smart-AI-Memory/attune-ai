---
name: cli
source: content/features/cli.md
tags:
- cli
- commands
type: task
---

# The attune command-line interface and its natural-language router

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
