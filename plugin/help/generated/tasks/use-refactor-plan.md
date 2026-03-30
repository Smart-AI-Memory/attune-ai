---
type: task
name: use-refactor-plan
tags: [skill, task]
source: plugin/skills/refactor-plan/SKILL.md
---

# Task: Use the refactor-plan skill

Code-level refactoring analysis and roadmap. Detects smells, duplication, complexity. Triggers on: refactor, tech debt, simplify, code smell, clean up, modularize, DRY.

Invoke with: `/refactor-plan <path to analyze>`

## Steps

1. **Scope the refactor-plan request**
   The skill asks scoping questions before running.

2. **Execute the refactor-plan workflow**
   Run the MCP tool with your scoped parameters.

   ```
   bash
attune workflow run refactor-plan --path <target>
   ```


## Related Topics
- **Reference**: Skill: refactor-plan — full reference
