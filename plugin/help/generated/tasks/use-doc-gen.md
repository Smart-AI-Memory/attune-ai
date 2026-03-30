---
type: task
name: use-doc-gen
tags: [skill, task]
source: plugin/skills/doc-gen/SKILL.md
---

# Task: Use the doc-gen skill

Generate documentation from source code — docstrings, READMEs, API references. Triggers on: generate docs, write documentation, document this, create README, API docs, doc-gen.

Invoke with: `/doc-gen <path or module to document>`

## Steps

1. **Scope the doc-gen request**
   The skill asks scoping questions before running.

2. **Execute the doc-gen workflow**
   Run the MCP tool with your scoped parameters.

   ```
   doc_gen(source_path="<target module>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: doc-gen — full reference
