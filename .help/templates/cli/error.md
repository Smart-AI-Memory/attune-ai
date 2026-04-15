---
type: error
feature: cli
depth: error
generated_at: 2026-04-14T15:11:27.250290+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI errors

Command execution failures, argument parsing issues, and routing problems in the Attune CLI.

## Common error signatures

- `SystemExit` with non-zero code — Command execution failed or invalid arguments provided
- `FileNotFoundError` — Preferences file or cost data file missing during routing or cost operations
- `ValueError` — Invalid skill name, malformed slash command, or bad cost export format
- `KeyError` — Missing required context fields in routing operations
- `PermissionError` — Cannot write to preferences file or cost export location

## Where errors originate

CLI errors typically emerge from these core operations:

- **Argument parsing** in `create_parser()` and `main()` — Invalid command combinations or missing required arguments
- **Routing decisions** in `HybridRouter.route()` — Unrecognized skills, malformed input, or corrupted preference data
- **Cost operations** in `cmd_costs*()` functions — Missing tracking data, file access issues, or invalid date ranges
- **Help system** in `cmd_help()` — Template file access problems or category lookup failures

## How to diagnose

1. **Check the exit code.** Run `echo $?` immediately after the failed command. Non-zero codes indicate specific failure modes that correspond to different error paths.

2. **Test with minimal input.** Strip down to the simplest failing case:
   - For routing issues: `attune "simple text"` vs `attune "/skill_name"`
   - For cost commands: `attune costs today` before trying complex exports
   - For help: `attune help` before specific categories

3. **Examine preferences file.** If routing behaves unexpectedly, check `~/.attune/preferences.json` for corruption. The `HybridRouter` fails silently on malformed preference data and falls back to basic routing.

4. **Verify file permissions.** CLI commands that write data (cost exports, preference updates) need write access to the target directories. Permission errors often manifest as generic "command failed" messages.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
