---
type: task
name: use-catalog
tags: [skill, task]
source: plugin/skills/catalog/SKILL.md
---

# Task: Use the catalog skill

Enumerate everything attune offers — every workflow, wizard, and tool, read live from the registries. Triggers on: catalog, list capabilities, browse, show all, what can attune do, list workflows, list wizards, what tools are there.

Invoke with: `/catalog [workflows|wizards|tools]`

## Steps

1. **Scope the catalog request**
   Answer the scoping questions before running.

2. **Run the tool**
   Call the `list_capabilities` MCP tool (no arguments):

   ```
   list_capabilities()
   ```

3. **Review catalog execution guidance**
   It returns `{workflows, wizards, tools}` — each a list of
   `{name, description}` — plus a `counts` summary, all read from
   `list_workflows()`, `list_wizards()`, and the live MCP tool
   registry at call time. **Do not hand-author or cache these
   lists** — always render what the tool returns.


## Related Topics
- **Reference**: Skill: catalog — full reference
