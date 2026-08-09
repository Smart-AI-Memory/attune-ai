---
type: task
name: use-workflow-orchestration
tags: [skill, task]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# Task: Use the workflow-orchestration skill

Run several analysis workflows together in one sweep. Triggers on: run all workflows, run multiple workflows, full analysis sweep, workflow orchestration.

Invoke with: `/workflow-orchestration <workflow: security, review, tests, perf, release, bugs, docs>`

## Steps

1. **Define goal**
   "What are you trying to accomplish?"

2. **Define scope**
   "Which path or files should I analyze?" Based on the answer, route to the appropriate workflow.

3. **Run the tool**
   Route to the matching MCP tool with the scoped path:

   ```
   security_audit(path="<user-specified path>")
code_review(path="<user-specified path>")
test_audit(path="<user-specified path>")
doc_audit(path="<user-specified path>")
   ```

4. **Choose follow-up action**
   Want me to fix the critical issues?; Should I run another workflow on the same path?; Want to generate tests for the flagged files?


## Related Topics
- **Reference**: Skill: workflow-orchestration — full reference
