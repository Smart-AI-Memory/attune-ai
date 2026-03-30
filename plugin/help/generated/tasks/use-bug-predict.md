---
type: task
name: use-bug-predict
tags: [skill, task]
source: plugin/skills/bug-predict/SKILL.md
---

# Task: Use the bug-predict skill

Predict likely bug locations from code patterns and complexity. Triggers on: predict bugs, find bugs, risky code, code risk, what might break, likely bugs.

Invoke with: `/bug-predict <path or directory to scan>`

## Steps

1. **Scope the bug-predict request**
   The skill asks scoping questions before running.

2. **Execute the bug-predict workflow**
   Run the MCP tool with your scoped parameters.

   ```
   bug_predict(path="<user-specified path>")
   ```


## Related Topics
- **Reference**: Skill: bug-predict — full reference
