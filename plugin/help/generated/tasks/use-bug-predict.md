---
type: task
name: use-bug-predict
tags: [skill, task]
source: plugin/skills/bug-predict/SKILL.md
---

# Task: Use the bug-predict skill

Predict likely bug locations from code patterns and complexity. Triggers on: predict bugs, find bugs, risky code, code risk, what might break, likely bugs, bug hotspots.

Invoke with: `/bug-predict <path or directory to scan>`

## Steps

1. **Define target path**
   "Which files or directory should I scan?" Default to `src/` if not specified.

2. **Define severity filter**
   "Show all findings, or only HIGH severity?"

3. **Run the tool**
   Call the `bug_predict` MCP tool with the scoped path:

   ```
   bug_predict(path="<user-specified path>")
   ```

4. **Run tool (option 2)**
   Or via CLI:

   ```bash
   uv run attune workflow run bug-predict --path <target>
   ```

5. **Review bug-predict execution guidance**
   ### Shared command workspace (preferred)

   When the generic command-workspace tools are available, open adapter
   `bug-predict` with the validated target path and `all`/`high` severity filter.
   The user's command invocation already authorizes this read-only scan: the
   workspace enters running state immediately and has no confirmation action.
   Run the existing `bug_predict` tool, publish optional `progress`, then publish
   one `scan_result` carrying the real success flag, risk score, findings,
   suggestions, or error. Present the terminal widget or its returned Markdown.
   A failed run must render **did not complete**, never a false zero-findings
   receipt. Fall back to the existing rich panel/Markdown behavior below when the
   shared tools are unavailable.


## Related Topics
- **Reference**: Skill: bug-predict — full reference
