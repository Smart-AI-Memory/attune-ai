---
type: task
name: models-task
feature: models
depth: task
generated_at: 2026-05-16T06:19:45.830318+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Work with models

Use the models feature when you need to configure authentication strategies, route tasks to the right model tier, or manage provider settings for your Attune workflows.

## Prerequisites

- Access to the project source code under `src/attune/models/`
- A Python environment where you can run `pytest`

## Steps

1. **Identify the area you want to change.**
   The models feature covers two main concerns. Choose the one that matches your goal:

   - **Authentication strategy** — controlled by `src/attune/models/auth_strategy.py`. Key functions:
     - `configure_auth_interactive()` — runs first-time interactive setup for an authentication strategy
     - `get_auth_strategy()` — retrieves the global `AuthStrategy` instance
     - `count_lines_of_code()` — counts lines in a Python file to inform tier and cost estimates
   - **CLI commands** — controlled by `src/attune/models/auth_cli.py`. Key functions:
     - `cmd_auth_setup()` — runs interactive authentication strategy setup
     - `cmd_auth_status()` — shows the current authentication strategy configuration
     - `cmd_auth_reset()` — resets or clears the authentication strategy configuration
     - `cmd_auth_recommend()` — returns an authentication recommendation for a specific file
     - `main()` — the main CLI entry point

2. **Read the function signature and docstring.**
   Before editing, confirm the function owns the behavior you need. Check its parameters, return type, and any `AuthStrategy` fields it reads or writes — for example, `default_mode`, `prefer_subscription`, and `cost_optimization`.

3. **Edit the function.**
   Keep your change consistent with the file's existing error-handling style and naming conventions. If you are modifying `AuthStrategy` fields, update both the dataclass definition and any callers that serialize or deserialize it with `to_dict()` / `from_dict()`.

4. **Run the related tests.**
   Verify your change does not introduce regressions:

   ```bash
   pytest -k "models"
   ```

## Verify success

The test run reports zero failures. If you changed a CLI command, run it directly and confirm the output matches the updated behavior:

```bash
python -m attune.models auth status
```

A correct result shows the active `AuthStrategy` fields — including `subscription_tier`, `default_mode`, and `setup_completed` — without errors.
