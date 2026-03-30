---
type: task
name: use-code-quality
tags: [skill, task]
source: plugin/skills/code-quality/SKILL.md
---

# Task: Use the code-quality skill

Code review and bug prediction to find quality issues, style violations, and likely bugs. Triggers on: review, quality, code review, analyze, lint, bugs, predict, code smell.

Invoke with: `/code-quality <path or directory to review>`

## Steps

1. **Scope the code-quality request**
   The skill asks scoping questions before running.

2. **Execute the code-quality workflow**
   Run the MCP tool with your scoped parameters.

   ```
   code_review(path="<user-specified path>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: code-quality — full reference
