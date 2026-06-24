---
type: error
name: cli-error
feature: cli
depth: error
generated_at: 2026-06-24T04:24:53.876139+00:00
source_hash: bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4
status: generated
---

# The attune command-line interface and its natural-language router

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `attune: command not found` | console script not on PATH | reinstall, or use `python -m attune.cli_minimal` | medium |
| `RuntimeWarning: coroutine 'route_user_input' was never awaited` | called `route_user_input` without `await` | it is async — `await` it / `asyncio.run` | high |
| A subcommand errors on args | wrong subcommand or arguments | `attune <group> --help` | low |
| `attune doctor` reports problems | environment/config issue | follow its diagnostics | medium |

### Risk areas

- **`route_user_input` is async.** `is_slash_command` and
  `SmartRouter.list_workflows` are sync; `route` is async (`route_sync`
  is the sync variant).
- **Console script vs module.** If `attune` isn't on PATH, `python -m
  attune.cli_minimal` always works.

### Diagnosis order

1. `attune --help` — is the CLI reachable?
2. `attune doctor` — environment check.
3. `attune <group> --help` — subcommand usage.
4. For routing in Python, remember `route_user_input` is async.
