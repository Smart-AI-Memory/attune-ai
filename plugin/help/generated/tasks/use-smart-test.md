---
type: task
name: use-smart-test
tags: [skill, task]
source: plugin/skills/smart-test/SKILL.md
---

# Task: Use the smart-test skill

Find test gaps and generate tests for uncovered code. Triggers on: generate tests, write tests, test coverage, find untested code, test gaps, smart test, what needs testing.

Invoke with: `/smart-test <path or module to test>`

## Steps

1. **Scope the smart-test request**
   The skill asks scoping questions before running.

2. **Execute the smart-test workflow**
   Run the MCP tool with your scoped parameters.

   ```
   test_audit(path="<target>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: smart-test — full reference
