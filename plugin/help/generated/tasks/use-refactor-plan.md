---
type: task
name: use-refactor-plan
tags: [skill, task]
source: plugin/skills/refactor-plan/SKILL.md
---

# Task: Use the refactor-plan skill

Code-level refactoring analysis and roadmap. Detects duplication and complexity. Triggers on: refactor, tech debt, simplify, clean up, modularize, DRY, restructure.

Invoke with: `/refactor-plan <path to analyze>`

## Steps

1. **Define target**
   "Which file or directory needs refactoring analysis?"

2. **Define focus**
   "Full analysis or specific concern?" - Full: `refactor_plan` (all areas) - Simplify: `simplify_code` (reduce complexity only)

3. **Define depth**
   "Quick scan or detailed roadmap?"

4. **Run the tool**
   Based on scope:

   - Full analysis: `refactor_plan(path="<target>")`
   - Simplify only: `simplify_code(path="<target>")`

   Or via CLI:

   ```bash
   attune workflow run refactor-plan --path <target>
   ```


## Related Topics
- **Reference**: Skill: refactor-plan — full reference
