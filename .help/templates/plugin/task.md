---
type: task
feature: plugin
depth: task
generated_at: 2026-04-14T15:22:31.898613+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Work with plugin

Use plugin when you need to customize Claude Code's runtime behavior through hooks, validation, or session management.

## Prerequisites

- Access to the project source code
- Familiarity with the files under plugin/**

## Identify the hook or component

1. **Determine which hook handles your use case:**
   - **Format on save**: `plugin/hooks/format_on_save.py` auto-formats Python files after Write/Edit operations
   - **Help freshness**: `plugin/hooks/help_freshness_check.py` checks template freshness on session start
   - **Error assistance**: `plugin/hooks/help_on_error.py` suggests help when Bash commands fail
   - **Git integration**: `plugin/hooks/help_post_commit.py` maintains .help/ directory after commits
   - **Security validation**: `plugin/hooks/security_guard.py` validates commands and file paths
   - **Welcome messages**: `plugin/hooks/welcome.py` displays session startup information

2. **Read the hook's main function** to confirm it handles your scenario. Each hook has a single `main()` entry point that processes specific events.

## Modify hook behavior

1. **Open the target hook file** and locate its `main()` function.

2. **Review the current logic flow** by tracing through the function's parameters and return values:
   - Format/help hooks read from stdin and process tool results
   - Security guard validates commands against `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES`
   - Welcome hook prints to stderr for Claude Code visibility

3. **Edit the hook logic** while preserving the function signature and return format:
   - Security functions return `(bool, str)` tuples
   - Main security validator returns `{'allowed': True/False}` dict
   - Other hooks typically return `None`

4. **Test your changes** by running the hook directly or through `pytest -k "plugin"`.

## Verify the modification works

Run a relevant operation to trigger your hook:
- Save a Python file to test format_on_save
- Start a new session to test help_freshness_check
- Run a failing command to test help_on_error
- Make a git commit to test help_post_commit
- Execute a restricted command to test security_guard

The hook should execute your modified behavior without errors.
