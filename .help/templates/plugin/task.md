---
type: task
name: plugin-task
feature: plugin
depth: task
generated_at: 2026-05-21T03:20:39.396433+00:00
source_hash: 5586c41f1c99c9715bfc73d5dc9622c7133d156e10d5ec551da7c26153748cf1
status: generated
---

# Work with plugin

Use the plugin module when you need to modify session-continuity hooks, resume prompts, or state discovery for Claude's workspace integration.

## Prerequisites

- Access to the project source code
- Familiarity with the plugin module structure
- Understanding of git workflows and spec discovery patterns

## Identify the component you need to modify

The plugin module contains four core components:

1. **Handoff CLI** (`plugin/hooks/_handoff_cli.py`) — Entry point for the `/handoff` slash command
2. **Resume prompt builder** (`plugin/hooks/_resume_prompt.py`) — Generates user-facing prompts with workspace context
3. **State discovery** (`plugin/hooks/_state.py`) — Finds in-flight specs and captures git state
4. **Transcript sizing** (`plugin/hooks/_transcript_size.py`) — Estimates context utilization for warnings

## Locate the specific function

Each component contains focused functions with single responsibilities:

- For CLI integration: `main()` in `_handoff_cli.py`
- For prompt generation: `build_resume_prompt()` in `_resume_prompt.py`
- For workspace discovery: `discover_specs()`, `git_state()`, or `workspace_roots()` in `_state.py`
- For context management: `estimate_utilization()` or `format_warning()` in `_transcript_size.py`

Read the function's docstring and parameters to confirm it handles your use case.

## Modify the function

1. Open the file containing your target function
2. Preserve the existing error handling and logging patterns
3. Match the naming conventions used in surrounding code
4. Test your changes incrementally as you work

## Verify your changes

Run the plugin-specific tests to catch regressions:

```bash
pytest -k "plugin"
```

Your modification works correctly when:
- All existing tests pass
- The function returns the expected type as documented
- Error conditions are handled consistently with the existing codebase
