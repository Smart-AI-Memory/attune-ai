---
type: task
name: models-task
feature: models
depth: task
generated_at: 2026-06-04T23:45:26.745205+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Work with models

Use the models module when you need to configure authentication strategies, route tasks to the right LLM provider, or manage model tiers based on historical telemetry.

## Prerequisites

- Access to the project source code under `src/attune/models/`
- Python environment with the project dependencies installed

## Steps

1. **Choose the entry point that matches your goal.**

   The models module exposes distinct functions for each authentication and routing concern:

   | Goal | Function | File |
   |---|---|---|
   | Run first-time auth setup interactively | `configure_auth_interactive()` | `auth_strategy.py` |
   | Read the active auth configuration | `get_auth_strategy()` | `auth_strategy.py` |
   | Measure a file's size before routing decisions | `count_lines_of_code()` | `auth_strategy.py` |
   | Set up auth via CLI | `cmd_auth_setup()` | `auth_cli.py` |
   | Inspect current CLI auth status | `cmd_auth_status()` | `auth_cli.py` |
   | Clear the CLI auth configuration | `cmd_auth_reset()` | `auth_cli.py` |
   | Get a routing recommendation for a specific file | `cmd_auth_recommend()` | `auth_cli.py` |

2. **Read the function signature and its dataclass.**

   Before calling or modifying a function, check its inputs and outputs against the relevant dataclass. For example, `configure_auth_interactive()` returns an `AuthStrategy` whose fields — including `subscription_tier`, `default_mode`, `prefer_subscription`, and `cost_optimization` — control downstream routing behaviour. Confirm that the fields you need are already present before adding new ones.

3. **Call or modify the function.**

   - To run interactive setup programmatically, call `configure_auth_interactive(module_lines=<int>)`. It returns a fully populated `AuthStrategy` instance.
   - To retrieve the current strategy without prompting, call `get_auth_strategy()`.
   - To determine how many tokens a module will consume before committing to a mode, call `count_lines_of_code(file_path)` and pass the result to `AuthStrategy.estimate_tokens()`.
   - To invoke the CLI directly, call `main()` from `auth_cli.py`; it returns an exit code of `1` on failure.

4. **Run the related tests.**

   Run `pytest -k "models"` to catch regressions before they affect other developers.

## Verify success

Your task succeeded when:

- `get_auth_strategy()` returns an `AuthStrategy` instance with `setup_completed` set to `True`.
- `pytest -k "models"` passes with no failures or errors.
- `cmd_auth_status()` prints the configuration you expect without raising an exception.
