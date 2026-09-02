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
   ### Shared command workspace (preferred)

   Open adapter `workflow-orchestration` with the goal, validated path, and exact
   ordered child list. Present its widget or returned Markdown. The bound
   `run_workflows` action requires explicit confirmation because it can invoke
   multiple paid workflows. Run only the returned children.

   Publish every real child outcome as one `child_result` carrying its name,
   status, detail, and exact probe. Then publish `orchestration_complete`. The
   adapter restores the requested order and synthesizes `MISSING` for any absent
   child; `FAIL`, `ERROR`, or `MISSING` keeps the aggregate failed, while warnings
   produce a visibly degraded receipt. Never collapse mixed outcomes into a
   clean summary. Preserve the same per-child receipts in compact text when the
   shared tools are unavailable.

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
