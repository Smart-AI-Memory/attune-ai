---
type: task
name: use-workflow-orchestration
tags: [skill, task]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# Task: Use the workflow-orchestration skill

Run analysis workflows — security, code review, tests, perf, bugs, docs, release. Triggers on: workflow, run, execute, analyze, security, review, test, perf, release, bugs, docs, audit.

Invoke with: `/workflow-orchestration <workflow: security, review, tests, perf, release, bugs, docs>`

## Steps

1. **Scope the workflow-orchestration request**
   The skill asks scoping questions before running.

2. **Execute the workflow-orchestration workflow**
   Run the MCP tool with your scoped parameters.

   ```
   security_audit(path="<user-specified path>")
code_review(path="<user-specified path>")
test_audit(path="<user-specified path>")
doc_audit(path="<user-specified path>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: workflow-orchestration — full reference
