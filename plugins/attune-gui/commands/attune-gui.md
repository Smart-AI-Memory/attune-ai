---
name: attune-gui
description: "Launch the attune-gui dashboard in the Cowork preview pane. Starts the FastAPI sidecar if not already running."
argument-hint: ""
---

# attune-gui Dashboard

Launch the attune-gui living-docs dashboard.

## Steps

1. Use the Bash tool to determine the attune-gui project path:
   - Run: `grep -s 'name = "attune-gui"' pyproject.toml`
   - If the grep returns a match, the resolved path is `.`
   - Else if `./attune-gui/` is a directory, the resolved path is `./attune-gui`
   - Else report: "attune-gui not found. Install with: pip install attune-gui then open Claude Code from the attune-gui project directory." and stop.

2. Check `.claude/launch.json`:
   - If it does not exist, or does not contain an `"attune-gui"` entry, write `.claude/launch.json`:
     ```json
     {
       "version": "0.0.1",
       "configurations": [
         {
           "name": "attune-gui",
           "runtimeExecutable": "uv",
           "runtimeArgs": ["run", "--directory", "<resolved-path>", "attune-gui", "--port", "8000"],
           "port": 8000
         }
       ]
     }
     ```
     Replace `<resolved-path>` with the path resolved in step 1.
   - If `.claude/launch.json` already contains an `"attune-gui"` entry, skip writing it.

3. Call `mcp__Claude_Preview__preview_start` with `name: "attune-gui"`.

4. Tell the user: "attune-gui is running at http://localhost:8000 — dashboard is open in the preview pane."
