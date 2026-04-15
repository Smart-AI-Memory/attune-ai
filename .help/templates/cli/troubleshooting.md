---
type: troubleshooting
feature: cli
depth: troubleshooting
generated_at: 2026-04-14T15:11:56.819379+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# Troubleshoot cli

## Before you start

The Attune AI CLI provides a hybrid routing system that combines natural language input with traditional CLI commands. It handles cost tracking, help browsing, and intelligent routing to Claude Code skills.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Command not recognized | Run `attune --help` to verify available commands and subcommands |
| Routing returns wrong skill | Check `HybridRouter` preferences file for learned mappings |
| Cost commands fail | Verify cost tracking data exists and is not corrupted |
| Help command shows no results | Confirm documentation templates are installed in the expected location |
| CLI crashes on startup | Check argument parsing in `create_parser()` and validate environment |

## Step-by-step diagnosis

1. **Test basic CLI functionality.**
   Run `attune --version` to confirm the CLI loads properly. If this fails, check your Python environment and package installation.

2. **Verify command structure.**
   Use `attune --help` to see all available commands. For subcommands, try `attune costs --help` or `attune help --help` to understand expected arguments.

3. **Check routing behavior.**
   If the hybrid router sends input to the wrong skill:
   - Test with a simple slash command like `/version`
   - Check if `is_slash_command()` correctly identifies your input
   - Examine the preferences file (default location varies by system)

4. **Enable debug output.**
   Add verbose flags if available, or modify the `main()` function temporarily to print intermediate values before the failure point.

5. **Test individual components.**
   For cost tracking issues, test each command separately:
   ```bash
   attune costs today
   attune costs export --output test.json
   ```

## Common fixes

- **Clear routing preferences.** If the hybrid router learned incorrect mappings, delete or reset the preferences file:
  ```bash
  # Find and remove the preferences file
  python -c "from attune.cli_router import HybridRouter; r = HybridRouter(); print(r.preferences_path)"
  ```

- **Reset cost tracking data.** For corrupted cost data:
  ```bash
  attune costs reset
  ```
  Note: This permanently deletes all cost history.

- **Reinstall with dependencies.** Version mismatches between Attune and its dependencies can break routing:
  ```bash
  pip uninstall attune
  pip install attune
  ```

- **Check argument parsing.** If commands fail with argument errors, verify you're using the correct syntax:
  ```bash
  attune help --category errors  # Not --categories
  attune costs export output.json  # May need --output flag
  ```

## Source files

- `src/attune/cli_minimal.py` — Main entry point and argument parsing
- `src/attune/cli_router.py` — Hybrid routing and preference learning
- `src/attune/cli_commands/` — Individual command implementations

**Tags:** `cli`, `commands`, `routing`, `costs`
