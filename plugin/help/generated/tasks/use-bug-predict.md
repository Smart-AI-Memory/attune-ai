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
   Call the `bug_predict` MCP tool with the scoped path: Or via CLI:

   ```
   bug_predict(path="<user-specified path>")
   ```

4. **Run tool (option 2)**

   ```
   uv run attune workflow run bug-predict --path <target>
   ```


## Related Topics
- **Reference**: Skill: bug-predict — full reference
