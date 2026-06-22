---
name: attune-gui
description: >
  Use this skill when the user wants to open, launch, or view the attune-gui
  dashboard, living docs, or template browser — without typing /attune-gui.
  Trigger on phrases like "open the dashboard", "show living docs", "launch the GUI",
  "show me the templates", "open attune-gui", or "I want to see the template dashboard".
  Do NOT trigger for general questions about attune-gui or requests to install it.
argument-hint: ""
---

# Launch attune-gui Dashboard

The user wants the dashboard open. Run the /attune-gui command steps:

1. Determine the attune-gui project path:
   - Run: `grep -s 'name = "attune-gui"' pyproject.toml`
   - Match → resolved path is `.`
   - No match but `./attune-gui/` exists → resolved path is `./attune-gui`
   - Neither → tell the user: "attune-gui not found. Install with: `pip install attune-gui` then open Claude Code from the attune-gui project directory." and stop.

2. Check `.claude/launch.json` — if it does not exist or has no `"attune-gui"` entry, write it:
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
   Replace `<resolved-path>` with the path from step 1. If the entry already exists, skip.

3. Call `mcp__Claude_Preview__preview_start` with `name: "attune-gui"`.

4. Tell the user: "attune-gui is running at http://localhost:8000 — dashboard is open in the preview pane."
