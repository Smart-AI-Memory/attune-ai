---
type: task
name: use-learn
tags: [skill, task]
source: plugin/skills/learn/SKILL.md
---

# Task: Use the learn skill

Progressive help for any topic. Repeat to go deeper: concept -> procedural -> reference. Triggers on: learn, explain, tell me more, how does, what is, help with, deeper.

Invoke with: `/learn <topic: security-audit, code-review, etc.>`

## Steps

1. **Run the tool**
   1. If the user provided a topic, call: Use the bare topic slug — the engine resolves the
right template type at each level: | User says | Topic slug |
|-----------|-----------|
| security audit | `security-audit` |
| code review | `code-review` |
| code quality | `code-quality` |
| bug predict | `bug-predict` |
| test gen | `test-generation` |
| release | `release-prep` |
| refactor | `refactor-plan` |
| doc gen | `doc-gen` | 2. If the user says "tell me more" or "go deeper"
   without a new topic, call `help_lookup` with the
   same topic again — it auto-advances to the next
   level. 3. If the user says "start from the beginning" or
   "reset", call: 4. If the user just finished a workflow, use
   `last_workflow` to skip the concept and start at
   procedural: 5. For file-based warnings:

   ```
   help_lookup(topic="<topic>", mode="progressive")
   ```

2. **Run tool (option 2)**

   ```
   help_lookup(topic="<topic>", mode="progressive", reset=true)
   ```

3. **Run tool (option 3)**

   ```
   help_lookup(
    topic="<topic>",
    mode="progressive",
    last_workflow="<workflow-name>"
)
   ```

4. **Run tool (option 4)**

   ```
   help_lookup(
    topic="warnings",
    mode="precursor",
    file_path="<path to file>"
)
   ```


## Related Topics
- **Reference**: Skill: learn — full reference
