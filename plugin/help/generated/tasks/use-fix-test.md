---
type: task
name: use-fix-test
tags: [skill, task]
source: plugin/skills/fix-test/SKILL.md
---

# Task: Use the fix-test skill

Auto-diagnose and fix failing tests — up to 3 attempts with re-runs. Triggers on: fix test, failing test, broken test, test error, why is this test failing, debug test.

Invoke with: `/fix-test <test file or pattern>`

## Steps

1. **Scope the fix-test request**
   The skill asks scoping questions before running.

2. **Execute the fix-test workflow**
   Run the MCP tool with your scoped parameters.

   ```
   bash
uv run pytest <target> -v --tb=short 2>&1 | tail -40
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: fix-test — full reference
